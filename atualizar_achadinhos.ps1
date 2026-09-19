Set-Location -Path $PSScriptRoot

python buscar_ofertas.py

git add achadinhos.csv
$data = Get-Date -Format "dd/MM/yyyy HH:mm"
git commit -m "Atualiza achadinhos - $data" 2>$null
git push 2>$null

Write-Output "Achadinhos atualizados em $data"
