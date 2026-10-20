# Run from the repo folder:  .\publish.ps1 "my message"
param([string]$m = "update profile")
git add -A
git commit -m $m
git pull --rebase -X theirs origin main   # keeps YOUR files if the stats bot changed the same ones
git push origin main
