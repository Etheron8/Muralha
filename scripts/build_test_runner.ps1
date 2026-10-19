$ErrorActionPreference = "Stop"

Write-Host "Construindo imagem isolada do Muralha..."
docker build -t muralha-test-runner:py312 -f sandbox/Dockerfile .
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao construir muralha-test-runner:py312"
}
Write-Host "Imagem criada. Mantenha MURALHA_ENABLE_SANDBOX=false até instalar e revisar os testes privados."
