#!/usr/bin/env bash
# Places each portrait raw/clip-N.mp4 on a 1600x900 #17030a canvas (phone 820px tall, 40px
# rounded corners), 30fps H.264, no audio, 0.3s fade-out, plus a poster JPG.
# Usage: bash portfolio-clips/compose.sh "N start duration poster_at" ...
set -euo pipefail
cd "$(dirname "$0")"

compose() {
  local n=$1 ss=$2 dur=$3 poster=$4
  local fade=$(awk "BEGIN{print $dur-0.3}")
  local vf="[0:v]fps=30,scale=-2:820,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(gt(abs(W/2-X),W/2-40)*gt(abs(H/2-Y),H/2-40),if(lte(hypot(40-(W/2-abs(W/2-X)),40-(H/2-abs(H/2-Y))),40),255,0),255)'[ph];
color=c=0x17030a:s=1600x900:r=30:d=$dur[bg];[bg][ph]overlay=(W-w)/2:(H-h)/2:shortest=1,fade=t=out:st=$fade:d=0.3,format=yuv420p"
  ffmpeg -loglevel error -y -ss "$ss" -t "$dur" -i "raw/clip-$n.mp4" -filter_complex "$vf" \
    -c:v libx264 -crf 26 -preset slow -an -movflags +faststart -pix_fmt yuv420p "dhan-$n.mp4"
  ffmpeg -loglevel error -y -ss "$poster" -i "dhan-$n.mp4" -frames:v 1 -q:v 4 "dhan-$n.jpg"
}

for spec in "${@:-1 0.8 10 5.5|3 0.6 6.2 4.5|4 1.0 10 4}"; do
  IFS='|' read -ra items <<< "$spec"
  for item in "${items[@]}"; do compose $item; done
done
