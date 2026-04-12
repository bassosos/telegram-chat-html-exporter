# telegram-chat-html-exporter (beta)
A tool for exporting Telegram chats into HTML files from cache4.db using [tlblobparser](https://github.com/bassosos/tlblobparser) module.
## Setup
### Install requirements
```bash
pip install -r requirements.txt
```
### Install tlblobparser
Clone the tlblobparser repository:
```bash
git clone https://github.com/bassosos/tlblobparser.git
```
Then copy the following files into the project directory:
- `tlblobparser.py`
- `layers/`
- `update.py`
## Usage
```bash
$ python tl_chats_export.py -h
usage: tl_chats_export.py [-h] [--output OUTPUT] [--ignore-cache] [--media MEDIA] db

tl_chats_export.py: extract Telegram chats from cache4.db in HTML format

positional arguments:
  db               Path to cache4.db file.

options:
  -h, --help       show this help message and exit
  --output OUTPUT  Output directory.
                   default: output.
  --ignore-cache   Ignore cache (force collect constructors)
  --media MEDIA    Path to telegram data folder and file_to_path.db (ex. `telegramDataFolder,file_to_path.db`)
```
### Media folder structure
When using the `--media` option, the `telegramDataFolder` should follow this layout:
```text
telegramDataFolder/
├── cache/
└── files/
    ├── Telegram/
    └── Telegram Files/
```
### Android data location
Telegram stores its internal data in:
```text
/storage/emulated/0/Android/data/org.telegram.messenger(.web)/files/
```
### Example
```bash
$ python tl_chats_export.py --media telegramDataFolder,file_to_path.db cache4.db
```
## Features
- Export Telegram chats to HTML
- Supports media extraction
