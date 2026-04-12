import os
import json
import sqlite3
import shutil
import argparse
from pathlib import Path
from pprint import pprint
from datetime import datetime
from tlblobparser import *
from tlhtml import TLHtml

self_name = ''
self_id = 0
utc_offset = 0
uids_names = {}

def export_messages(uid, conn_cache, cursor_cache, root_path, telegram_data_path=None, file_to_path_db_path=None):
    global self_name
    global utc_offset
    global uids_names
    
    try:
        dialog_name = uids_names[uid]
    except KeyError as e:
        print(f'Invalid uid: {e}')
        return
    
    print(f'Exporting: {dialog_name}...')
    restricted_chars = {'\\':'','/':'',':':'','*':'','<':'','>':'','|':'','.':''}
    dialog_folder_name = dialog_name.translate(str.maketrans(restricted_chars))
    
    dialog_path = root_path / dialog_folder_name
    dialog_path.mkdir(exist_ok=True)
    
    cursor_cache.execute(f'SELECT date, data, out, mid, reply_to_message_id FROM messages_v2 WHERE uid={uid} ORDER BY date ASC')
    conn_cache.commit()
    messages = cursor_cache.fetchall()
    
    if len(messages) == 0:
        cursor_cache.execute(f'SELECT date, data, out, mid, reply_to_message_id FROM messages_v2 WHERE uid=-{uid} ORDER BY date ASC')
        conn_cache.commit()
        messages = cursor_cache.fetchall()
        if len(messages) == 0:
            print('No messages')
            return
    
    html = TLHtml(open(dialog_path / 'messages.html', 'w', encoding='utf-8'), utc_offset, self_name, uid, dialog_path, file_to_path_db_path, telegram_data_path)
    html.set_dialog_name(dialog_name)
    
    previous_date = messages[0][0]
    html.write_new_date(previous_date)
    
    for message in messages:
        date = message[0]
        data = message[1]
        is_out = message[2]
        msgid = message[3]
        reply_to = message[4]
        
        parser = TLConstructor(data)
        
        from_name = ''
        if is_out:
            from_name = self_name
        else:
            if parser.is_set('from_id'):
                from_name = str(parser['from_id'][0].content())
                if from_name not in uids_names:
                    from_name = 'unknown'
                else:
                    from_name = uids_names[from_name]
            else:
                from_name = dialog_name
        
        if parser.get_predicate() == 'message':
            message_string = parser['message']
            post_author = parser['post_author']
            forward = parser['fwd_from']
            media = None
            
            if telegram_data_path is not None:
                media = parser['media']
                
            html.insert_message(from_name=from_name, date=date, message_string=message_string, message_id=msgid, reply_to=reply_to, post_author=post_author, media=media)
        else: # elif parser.get_predicate() == 'messageService'
            if parser['action'].get_predicate() == 'messageActionPhoneCall':
                html.insert_message(from_name=from_name, call=parser, date=date, message_id=msgid)
    html.finish()
        
def main():
    global self_id
    global self_name
    global uids_names
    global utc_offset
    
    parser = argparse.ArgumentParser(
        description='tl_chats_export.py: extract Telegram chats from cache4.db in HTML format',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--output',
        help='Output directory.\ndefault: output.'
    )
    parser.add_argument(
        '--ignore-cache',
        action='store_true',
        help='Ignore cache (force collect constructors)'
    )
    parser.add_argument(
        '--media',
        help='Path to telegram data folder and file_to_path.db (ex. `telegramDataFolder,file_to_path.db`)'
    )
    parser.add_argument(
        'db',
        help='Path to cache4.db file.'
    )

    args = parser.parse_args()
    cache4_path = args.db
    output_directory = args.output
    ignore_cache = args.ignore_cache
    
    if args.media is not None:
        telegram_data_path, file_to_path_db_path = args.media.split(',')
    else:
        telegram_data_path = None
        file_to_path_db_path = None
    
    conn_cache = sqlite3.connect(cache4_path)
    cursor_cache = conn_cache.cursor()
    if not os.path.exists('cache.json') or ignore_cache:
        if not TLConstructor.collect_constructors('layers', conn_cache, cursor_cache):
            print('Please update your schemas!')
            exit(-1)
    else:
        TLConcstructor.load_cache('cache.json')
        print('cache loaded')
    
    cursor_cache.execute('SELECT data FROM users')
    conn_cache.commit()
    users_data = cursor_cache.fetchall()
    
    for user_data in users_data:
        parser = TLConstructor(user_data[0])
        if parser.is_set('self'):
            if parser.is_set('first_name'):
                self_name = parser['first_name'].content()
            if parser.is_set('last_name'):
                self_name += ' ' + parser['last_name'].content()
    
    cursor_cache.execute('SELECT did FROM dialogs')
    conn_cache.commit()
    dialogs = [str(row[0]) for row in cursor_cache.fetchall()]
    
    cursor_cache.execute('SELECT uid, name FROM users')
    conn_cache.commit()
    users = dict((str(uid), name) for uid, name in cursor_cache.fetchall())
    
    cursor_cache.execute('SELECT uid, name FROM chats')
    conn_cache.commit()
    uids_names = dict((str(uid), name) for uid, name in cursor_cache.fetchall())
    uids_names = uids_names | users
    del users
    
    utc_offset = int(input('UTC Offset: '))
    print(' = = = = = = = = = = = = = = = = = = = DIALOGS = = = = = = = = = = = = = = = = = = = ')
    i = 1
    unknown_count = 1
    for dialog in dialogs:
        try:
            if dialog not in uids_names:
                _dialog = dialog.lstrip('-')
                key_val = {dialog: uids_names[_dialog]}
                uids_names.pop(_dialog)
                uids_names.update(key_val)
            if uids_names[dialog] == ';;;':
                uids_names[dialog] = f'unknown{unknown_count}'
                unknown_count += 1
            print(f'{i}: {uids_names[dialog]}')
        except KeyError as e:
            pass
        i += 1
    user_sel = input('Select dialog to export (`0` for all): ')
    user_sel = int(user_sel)
    
    root_path = None
    if output_directory == None:
        root_path = Path('output')
    else:
        root_path = Path(output_directory)
    root_path.mkdir(exist_ok=True)
    
    js_path = root_path / 'js'
    css_path = root_path / 'css'
    images_path = root_path / 'images'
    js_path.mkdir(exist_ok=True)
    css_path.mkdir(exist_ok=True)
    images_path.mkdir(exist_ok=True)
    
    shutil.copy('style.css', css_path)
    shutil.copy('script.js', js_path)
    shutil.copytree('images', images_path, dirs_exist_ok=True)
    
    if user_sel == 0:
        for dialog in dialogs:
            export_messages(dialog, conn_cache, cursor_cache, root_path, telegram_data_path, file_to_path_db_path)
    else:
        export_messages(dialogs[user_sel-1], conn_cache, cursor_cache, root_path, telegram_data_path, file_to_path_db_path)
        
if __name__ == '__main__':
    main()