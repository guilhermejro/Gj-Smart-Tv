# GJ Smart TV

Player IPTV desktop (PySide6 + libmpv + SQLite) para Linux Mint / Ubuntu.

## Estado atual (MVP)

Implementado e testado automaticamente (40 testes): banco SQLite, fontes M3U/M3U8 persistentes
(várias, padrão, editar/ativar/excluir), parser, download seguro, favoritos, histórico, preferências,
mascaramento de credenciais e interface (smoke test offscreen).
**Reprodução com libmpv:** o código está escrito, mas só pode ser validado em uma máquina com libmpv e
um stream real. Teste-a no seu computador antes de considerá-la concluída.
Ainda não feito: cache offline da lista de canais (a *fonte* é preservada, os canais exigem rede),
validação em Windows real, suporte a D-pad.

## Windows 11

Veja `README_WINDOWS.md` (instalador por usuário, sem administrador) e a seção de segurança lá.

## 1. Dependências do sistema (Linux Mint 21/22, Ubuntu 22.04/24.04)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libmpv2 \
    libxcb-cursor0 libxkbcommon-x11-0 libegl1 libgl1
# Mint/Ubuntu mais antigos podem usar libmpv1 no lugar de libmpv2
```

## 2. Ambiente virtual e execução

```bash
cd gj-smart-tv
python3 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements.lock   # versões e hashes fixos
python main.py
```

O vídeo é embutido pelo identificador de janela (X11). Em sessões Wayland, se o vídeo não aparecer:
`QT_QPA_PLATFORM=xcb python main.py`.

## 3. Testes

```bash
python -m pytest -q
```

## 4. Erros de biblioteca compartilhada

```bash
ldconfig -p | grep libmpv          # deve listar libmpv.so.2 (ou .so.1)
python -c "import mpv"             # "Cannot find libmpv" => instale libmpv2
python -c "import PySide6.QtWidgets"   # erro do plugin xcb => instale libxcb-cursor0
QT_DEBUG_PLUGINS=1 python main.py 2>&1 | grep -i "cannot\|missing"
```
O app abre mesmo sem libmpv e mostra a mensagem de instalação na tela do player.

## 5. Executável (PyInstaller)

```bash
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean gj-smart-tv.spec
# saída: dist/gj-smart-tv/
```
O PyInstaller **não** embute a libmpv do sistema: o computador de destino precisa ter `libmpv2` instalado.

## 6. Lançador `.desktop`

Crie `~/.local/share/applications/gj-smart-tv.desktop` (ajuste o caminho):

```ini
[Desktop Entry]
Type=Application
Name=GJ Smart TV
Comment=Player IPTV
Exec=/caminho/para/dist/gj-smart-tv/gj-smart-tv
Terminal=false
Categories=AudioVideo;Video;Player;
```
Para rodar do código-fonte: `Exec=/caminho/gj-smart-tv/.venv/bin/python /caminho/gj-smart-tv/main.py`.

## 7. Desinstalar

```bash
rm -rf ~/.local/share/gj-smart-tv            # banco (fontes, favoritos) e logs
rm -f  ~/.local/share/applications/gj-smart-tv.desktop
rm -rf /caminho/gj-smart-tv                  # projeto, .venv e dist/
```

## Atalhos

Espaço play/pause · F tela cheia · Esc sair da tela cheia/voltar · ↑/↓ navegar · Enter selecionar ·
M mudo · Ctrl+F buscar · Ctrl+R atualizar playlist.

## Privacidade

O link da lista fica só no SQLite local (`~/.local/share/gj-smart-tv/gjtv.db`). Logs mascaram usuário,
senha e tokens. Nenhum dado é enviado a terceiros; apenas a playlist e os logos indicados por ela são baixados.
