# GJ Smart TV no Windows 11

> **Aviso honesto:** estes scripts foram escritos e revisados, mas **nunca executados em um Windows**
> (o ambiente de desenvolvimento era Linux). O que foi verificado: a suíte de testes, o build do PyInstaller
> no Linux com o mesmo `.spec` e a extração do `libmpv-2.dll` do arquivo com o hash fixado. A parte Windows
> (DPAPI, instalador, DLL) precisa do seu primeiro teste real.

## Pré-requisitos (uma vez)

```powershell
winget install Python.Python.3.12
winget install Microsoft.VCRedist.2015+.x64
winget install 7zip.7zip
winget install JRSoftware.InnoSetup      # opcional: só para gerar o instalador .exe
```

## Gerar o aplicativo e o instalador

Em um PowerShell, na pasta do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File windows\build.ps1
```

O script: cria `.venv`, instala as dependências com `--require-hashes` (`requirements.lock`), baixa o
`libmpv-2.dll` **e só o instala se o SHA-256 do download conferir**, roda os testes, gera
`dist\gj-smart-tv\gj-smart-tv.exe` e, havendo Inno Setup, `installer\GJ-Smart-TV-Setup-0.2.0.exe`
com `installer\SHA256SUMS.txt`.

O instalador é **por usuário e não pede administrador**. Atalho no Menu Iniciar; ao desinstalar ele
pergunta se você quer apagar fontes, favoritos e histórico.

## Rodar sem instalar (desenvolvimento)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File windows\fetch_libmpv.ps1
.\.venv\Scripts\python main.py
```

## SmartScreen e antivírus

O instalador **não é assinado**; o Windows mostrará "Windows protegeu o computador" (Mais informações →
Executar assim mesmo). Se for distribuir a terceiros, assine com um certificado de assinatura de código
(`signtool`). O UPX foi desligado de propósito para reduzir falsos positivos.
O `libmpv-2.dll` tem ~120 MB, por isso o instalador é grande.

## Licença do libmpv

O build do libmpv é de terceiros (shinchiro/mpv-winbuild-cmake) e tem licença GPL/LGPL. Para uso pessoal,
o script apenas baixa. Se você **redistribuir** o instalador com o DLL embutido, confira as obrigações da licença.

## Segurança: o que foi aplicado

- **Instalação sem administrador**; dados em `%LOCALAPPDATA%\gj-smart-tv`.
- **URLs protegidas com DPAPI** (vinculadas ao seu usuário do Windows): fontes, favoritos e histórico
  não ficam em texto puro no `gjtv.db`; copiar o arquivo para outro usuário ou PC não revela o link.
  No campo do link, o texto fica oculto fora da edição.
- **Chaves de favoritos/histórico** viram hash (sem URL); bancos antigos são migrados sozinhos.
- **Logs** mascaram usuário, senha, tokens e segmentos que parecem credenciais, inclusive em erros.
- **Download da playlist**: só http/https; limite de 50 MB já descompactado; limite de 90 s; bloqueia
  redirecionamento de HTTPS para HTTP e da internet para a rede local (localhost, 192.168.x, 169.254.x).
- **Parser**: limite de 300 mil canais, linhas > 4 KB descartadas, caracteres de controle removidos, só
  esquemas de stream conhecidos (nunca `file://`).
- **Logos**: só http/https de hosts públicos; limite de 2 MB por imagem e de memória na decodificação.
- **mpv**: ignora `mpv.conf` e scripts de terceiros; `ytdl` desligado; `libmpv-2.dll` só é procurado na pasta do app.
  O diretório atual é removido da busca de DLLs (anti DLL hijacking).
- **Dependências** com versões e hashes fixos; aviso quando o link usa HTTP com credenciais.

### Limites que você deve conhecer

- Os streams em si (HTTP puro, RTMP...) não são criptografados por este app; só a sua fonte, se for HTTPS.
- DPAPI protege contra outro usuário/outro PC, **não** contra malware rodando como você.
- Se você reinstalar o Windows ou trocar de usuário, as fontes salvas ficarão ilegíveis: cadastre-as de novo.
- O Windows não restringe a leitura do banco por permissões de arquivo além da pasta do usuário.

## Desinstalar

Configurações → Aplicativos → GJ Smart TV → Desinstalar (responda se quer apagar os dados), ou apague
`%LOCALAPPDATA%\gj-smart-tv` manualmente.
