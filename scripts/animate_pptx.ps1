# animate_pptx.ps1 — add native PowerPoint animation to a built deck (Windows + PowerPoint).
#
# Adds, per slide:
#   ① Slide transition  — Morph (PP2019/365) with a Fade fallback for older PowerPoint.
#   ② Element build      — CONTENT shapes fade in, staggered (cascade), on slide entry.
#                          The title and the full-bleed background are SKIPPED so they don't
#                          flash — the title morphs (③) and the background is carried by Morph.
#   ③ Title morph        — on every slide the headline (largest-font *lettered* text shape) is
#                          renamed "!!title". A name starting with "!!" forces PowerPoint's Morph
#                          to MATCH that shape across consecutive slides, so the title glides/scales
#                          between its two positions every transition (kinetic typography). Numeric
#                          stats ("100%", "0") are excluded from the title pick so they never morph.
#
# Mechanism: PowerPoint COM writes the (valid) build timing + a Fade transition wrapper, then
# a zip pass rewrites the Fade inside the p14 mc:Choice into <p14:morph> (Fade stays in the
# mc:Fallback). COM guarantees valid OOXML; we only swap one element. (python-pptx is banned.)
#
# Re-runnable: existing build timing is cleared per slide first, so running twice is idempotent.
#
# Usage:
#   powershell -File animate_pptx.ps1 -In deck.pptx -Out deck-animated.pptx [-Build] [-BuildSlides "all"|"2,6"] [-Dur 0.9] [-NoTitleMorph]
param(
  [Parameter(Mandatory)][string]$In,
  [Parameter(Mandatory)][string]$Out,
  [switch]$Build,                 # add element-build cascade (content shapes fade in)
  [string]$BuildSlides = "all",   # "all" (default) or "2,6" (1-based slide numbers)
  [switch]$NoTitleMorph,          # disable the forced title morph (title then builds like content)
  [double]$Dur = 0.9              # transition duration (seconds)
)

Copy-Item $In $Out -Force

# Encoding-safe "contains a real word" test (ASCII letters or Hangul AC00-D7A3).
# NOTE: do NOT use a Korean regex literal here — PowerShell 5.1 reads a BOM-less UTF-8
# .ps1 as the ANSI codepage (cp949 on a KR box), which corrupts non-ASCII literals.
function Test-HasWord([string]$t) {
  foreach ($ch in $t.ToCharArray()) {
    $c = [int][char]$ch
    if (($c -ge 65 -and $c -le 90) -or ($c -ge 97 -and $c -le 122) -or ($c -ge 0xAC00 -and $c -le 0xD7A3)) { return $true }
  }
  return $false
}

$ppt = $null
try {
  $ppt = New-Object -ComObject PowerPoint.Application
  $pres = $ppt.Presentations.Open($Out, $false, $false, $false)
  $n  = $pres.Slides.Count
  $SW = $pres.PageSetup.SlideWidth
  $SH = $pres.PageSetup.SlideHeight
  $buildSet = if ($BuildSlides -eq "all") { 1..$n } else { $BuildSlides -split ',' | ForEach-Object { [int]$_ } }

  for ($s = 1; $s -le $n; $s++) {
    $sl  = $pres.Slides.Item($s)
    $cnt = $sl.Shapes.Count

    # clear any pre-existing build animation so re-runs are idempotent
    try { $seq = $sl.TimeLine.MainSequence; while ($seq.Count -gt 0) { $seq.Item(1).Delete() } } catch {}

    # ① transition (written as Fade now; the zip pass morphs it)
    $sl.SlideShowTransition.EntryEffect   = 3849      # a Fade variant (confirmed)
    $sl.SlideShowTransition.Duration      = $Dur
    $sl.SlideShowTransition.AdvanceOnClick = $true

    # classify ALL shapes ONCE on the stable (cleared) timeline, capturing the shape ref + chosen effect.
    # Reading shape props (.Name/.Width/.Text) DURING the build — after AddEffect calls have started —
    # throws intermittently (COM goes flaky and the catch silently drops the shape), so we decide
    # everything here and the build loop then touches NO properties, only AddEffect on the stored refs.
    #   title = largest-font LETTERED text shape (morphs);  stat = pure-number, height-gated (Zoom);
    #   full-bleed bg = skip (carried by Morph);  everything else = Fly In (slides up).
    $title = $null; $titleIdx = -1; $maxsz = 0.0; $plan = @()
    for ($i = 1; $i -le $cnt; $i++) {
      $sh = $sl.Shapes.Item($i)
      $eff = 3; $skip = $false
      # full-bleed bg check in its OWN try — .Width throws on some shape types and must NOT abort the
      # text/title detection below (that was the bug: a leading .Width read killed the whole classify try).
      try { if (($sh.Width -ge 0.95 * $SW) -and ($sh.Height -ge 0.95 * $SH)) { $skip = $true } } catch {}
      try {
        if ($sh.HasTextFrame -and $sh.TextFrame.HasText) {
          $t = ($sh.TextFrame.TextRange.Text).Trim()
          if (Test-HasWord $t) {                                 # a headline (has real words)
            $sz = [double]$sh.TextFrame.TextRange.Font.Size      # uniform for a headline; -2 if mixed
            if ($sz -gt $maxsz) { $maxsz = $sz; $title = $sh; $titleIdx = $i }
          } elseif (($t -match '[0-9]') -and (($t -replace '[0-9%\.\,\+\-xX/ ]', '') -eq '') -and ($sh.Height -ge 30)) {
            $eff = 26                                            # pure-number stat ("100%", "4.5x") -> Zoom
          }
        }
      } catch {}
      $plan += [pscustomobject]@{ sh = $sh; eff = $eff; skip = $skip }
    }
    $titleTxt = ""
    if (($titleIdx -ge 1) -and -not $NoTitleMorph) {
      $title.Name = "!!title"                                    # force Morph to match the title across slides
      try { $titleTxt = ($title.TextFrame.TextRange.Text -replace '\s+', ' ').Trim() } catch {}
      $plan[$titleIdx - 1].skip = $true                          # title morphs -> no build
    }

    # ② build cascade — apply the precomputed plan: content shapes MOVE in (Fly In = slide up), big
    #    numbers Zoom (pop), each with an ease-out landing + staggered start (cascade rhythm). No flat
    #    fade. Fly In / Zoom render on EVERY PowerPoint version (Morph needs 2019+), so motion survives
    #    downlevel even where the Morph transition falls back to a plain Fade.
    $added = 0; $zoomed = 0
    if ($Build -and ($buildSet -contains $s)) {
      $j = 0
      foreach ($p in $plan) {
        if ($p.skip) { continue }
        try {
          $e = $sl.TimeLine.MainSequence.AddEffect($p.sh, $p.eff, 0, 2)   # trigger = withPrevious
          $e.Timing.TriggerDelayTime = [Math]::Round($j * 0.05, 2)        # tight stagger → snappy cascade
          $e.Timing.Duration = $(if ($p.eff -eq 26) { 0.65 } else { 0.5 })
          try { $e.Timing.Decelerate = 0.6 } catch {}                     # ease-out = soft landing (감각적)
          if ($p.eff -eq 26) { $zoomed++ }
          $j++; $added++
        } catch {}
      }
    }
    Write-Output ("  slide{0}: title='{1}' ({2}pt) morph  builds={3} (flyin={4} zoom={5})" -f $s, $titleTxt, $maxsz, $added, ($added - $zoomed), $zoomed)
  }
  $pres.Save(); $pres.Close()
} finally {
  if ($ppt) { try { $ppt.Quit() } catch {}; [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) }
}

# zip pass: normalize EVERY slide's transition to a Morph (p14) block with a Fade fallback.
# COM serializes the Fade inconsistently — sometimes a bare <p:transition>, sometimes already wrapped
# in mc:AlternateContent — so we replace whichever form is present with the canonical morph block.
# This guarantees morph on all slides (the earlier single-element swap only caught the wrapped form).
Add-Type -AssemblyName System.IO.Compression.FileSystem
$opt = [System.Text.RegularExpressions.RegexOptions]::Singleline
$MORPH  = '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"><mc:Choice xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" Requires="p14"><p:transition spd="slow" p14:dur="900"><p14:morph option="byObject"/></p:transition></mc:Choice><mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback></mc:AlternateContent>'
$reAlt  = '<mc:AlternateContent[^>]*><mc:Choice[^>]*Requires="p14"><p:transition.*?</mc:AlternateContent>'
$reBare = '<p:transition[^>]*>.*?</p:transition>|<p:transition[^>]*/>'
$zip = [System.IO.Compression.ZipFile]::Open($Out, 'Update')
$swapped = 0
try {
  foreach ($e in @($zip.Entries | Where-Object { $_.FullName -match '^ppt/slides/slide\d+\.xml$' })) {
    $sr = New-Object System.IO.StreamReader($e.Open()); $xml = $sr.ReadToEnd(); $sr.Dispose()
    if     ([regex]::IsMatch($xml, $reAlt,  $opt)) { $new = [regex]::Replace($xml, $reAlt,  $MORPH, $opt) }
    elseif ([regex]::IsMatch($xml, $reBare, $opt)) { $new = [regex]::Replace($xml, $reBare, $MORPH, $opt) }
    else { $new = $xml }
    if ($new -ne $xml) {
      $st = $e.Open(); $st.SetLength(0); $sw = New-Object System.IO.StreamWriter($st); $sw.Write($new); $sw.Dispose()
      $swapped++
    }
  }
} finally { $zip.Dispose() }
Write-Output "animated -> $Out  (morph on $swapped slides; title-morph=$(-not $NoTitleMorph); build=$($Build.IsPresent) on [$BuildSlides])"
