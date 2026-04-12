import sqlite3
import random
import shutil
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from pathlib import Path
from mutagen import File
from tlblobparser import *
import os

class TLHtml:
    def __init__(self, file, utc_offset, self_name, dialog_id, dialog_path, file_to_path_db_path=None, telegram_data_path=None):
        self.file = file
        self.html = '<!DOCTYPE html><html><head><meta charset="utf-8"/><title>Exported Data</title><meta content="width=device-width, initial-scale=1.0" name="viewport"/><link href="../css/style.css" rel="stylesheet"/><script src="../js/script.js" type="text/javascript"></script></head><body onload="CheckLocation();"><div class="page_wrap"><div class="page_body chat_page"><div class="history"></div></div></div></body></html>'
        self.soup = BeautifulSoup(self.html, 'lxml')
        self.history = self.soup.find('div', class_='history')
        self.date_count = 1
        self.name_userpics = {}
        self.utc_offset = utc_offset
        self.sign = '+' if self.utc_offset >= 0 else '-'
        self.tz = timezone(timedelta(hours=self.utc_offset))
        self.self_name = self_name
        self.last_date = 9999999999
        self.last_from_name = ''
        self.dialog_id = dialog_id
        
        if file_to_path_db_path is not None:
            self.conn = sqlite3.connect(file_to_path_db_path)
            self.cursor = self.conn.cursor()
            self.telegram_data_path = Path(telegram_data_path)
        
        self.video_files_path = dialog_path / 'video_files'
        self.photos_path = dialog_path / 'photos'
        self.round_video_messages_path = dialog_path / 'round_video_messages'
        self.voice_messages_path = dialog_path / 'voice_messages'
        self.stickers_path = dialog_path / 'stickers'
        self.files_path = dialog_path / 'files'
        
        self.video_files_path.mkdir(exist_ok=True)
        self.photos_path.mkdir(exist_ok=True)
        self.round_video_messages_path.mkdir(exist_ok=True)
        self.voice_messages_path.mkdir(exist_ok=True)
    def set_dialog_name(self, dialog_name):
        self.dialog_name = dialog_name
    
        page_wrap = self.soup.find('div', class_='page_wrap')
        page_header = self.soup.new_tag('div', attrs={'class' :'page_header'})
        content = self.soup.new_tag('div', attrs={'class': 'content'})
        text = self.soup.new_tag('div', attrs={'class': ['text', 'bold']})
        text.string = dialog_name
        
        content.append(text)
        page_header.append(content)
        
        page_wrap.insert(0, page_header)
    def write_new_date(self, date):
        message_service = self.soup.new_tag('div', attrs={'class': ['message', 'service']}, id=f'message-{str(self.date_count)}')
        body_details = self.soup.new_tag('div', attrs={'class': ['body', 'details']})
        body_details.string = datetime.fromtimestamp(date).strftime('%d %B %Y')
        
        message_service.append(body_details)
        self.history.append(message_service)
        self.date_count += 1
    def insert_message(self, call = False, message_string=None, message_id='', from_name='', date=None, media=None, reply_to=0, post_author=None, forward=None):
        if (datetime.fromtimestamp(date, tz=self.tz).date()) > (datetime.fromtimestamp(self.last_date, tz=self.tz).date()):
            self.write_new_date(date)    
        message_div = self.soup.new_tag('div', attrs={'class': ['message', 'default', 'clearfix'], 'id': f'message{message_id}'})
        body_div = self.soup.new_tag('div', attrs={'class': 'body'})
        
        if (self.last_from_name != from_name) or (self.last_from_name == self.last_from_name and date - self.last_date >= 180):
            userpic_wrap_div = self.soup.new_tag('div', attrs={'class': ['pull_left', 'userpic_wrap']})
            if from_name not in self.name_userpics:
                self.name_userpics.update({from_name: f'userpic{random.randint(1, 8)}'})
            userpic_div = self.soup.new_tag('div', attrs={'class': ['userpic', self.name_userpics[from_name]], 'style': 'width: 42px; height: 42px'})
            initials_div = self.soup.new_tag('div', attrs={'class': 'initials', 'style': 'line-height: 42px'})
            initials_div.string = f' {from_name[0]} '
            
            userpic_div.append(initials_div)
            userpic_wrap_div.append(userpic_div)
            message_div.append(userpic_wrap_div)
            
            from_name_div = self.soup.new_tag('div', attrs={'class': 'from_name'})
            from_name_div.string = f' {from_name} '
            body_div.append(from_name_div)
        if (self.last_from_name == from_name) and (date - self.last_date <= 180):
            message_div['class'].append('joined')
        
        dt = datetime.fromtimestamp(date, self.tz)
        right_date_div = self.soup.new_tag('div', attrs={'class': ['pull_right', 'date', 'details'], 'title': f'{dt.strftime("%d.%m.%Y %H:%M:%S")} UTC{self.sign}{abs(self.utc_offset):02}:00'})
        right_date_div.string = f' {dt.strftime("%H:%M")} '
        
        body_div.append(right_date_div)
        
        if reply_to:
            reply_to_details_div = self.soup.new_tag('div', attrs={'class': ['reply_to', 'details']})
            reply_to_details_div.string = ' In reply to '
            goto_a = self.soup.new_tag('a', attrs={'href': f'#go_to_message{reply_to}', 'onclick': f'return GoToMessage({reply_to})'})
            goto_a.string = 'this message'
            reply_to_details_div.append(goto_a)
            body_div.append(reply_to_details_div)
        if forward:
            body_div['class'].append('forwarded')
            from_name_div = self.soup.new_tag('div', attrs={'class': 'from_name'})
            from_name_div.string = forward['from_name'].content()
            dt = datetime.fromtimestamp(forward['date'].content())
            date_span = self.soup.new_tag('span', attrs={'class': ['date', 'details'], 'title': f'{dt.strftime("%d.%m.%Y %H:%M:%S")} UTC{self.sign}{abs(self.utc_offset):02}:00'})
            date_span.string = f' {dt.strftime("%H:%M")} '
            from_name_div.append(date_span)
            body_div.append(from_name_div)
        if media:
            def find_media(paths):
                exts = ('jpg', 'png', 'mp4', 'ogg', 'm4a', 'mp3')
                return_value = []
                for path in paths:
                    ext = os.path.splitext(path[0])[1][1:]
                    if ext in exts:
                        path_obj = path[0].split('org.telegram.messenger/')[1]
                        path_obj = Path(path_obj)
                        local_path = self.telegram_data_path / path_obj
                        if local_path.exists():
                            return_value.append(local_path)
                return return_value
            if media.get_predicate() != 'messageMediaEmpty':            
                predicate = media.get_predicate()
                self.cursor.execute(f'SELECT path FROM paths_by_dialog_id WHERE message_id={message_id} AND dialog_id={self.dialog_id}')
                self.conn.commit()
                results = self.cursor.fetchall()
                media_wrap_div = self.soup.new_tag('div', attrs={'class': ['media_wrap', 'clearfix']})
                
                found = False
                if len(results) > 0:
                    local_paths = find_media(results)
                    if local_paths:
                        if predicate == 'messageMediaPhoto':
                            found = True
                            local_path = max(local_paths, key=lambda p: p.stat().st_size)
                            shutil.copy2(local_path, self.photos_path)
                            photo_wrap_a = self.soup.new_tag('a', attrs={'class': ['photo_wrap', 'clearfix', 'pull_left'], 'href': 'photos/' + local_path.name})
                            photo_img = self.soup.new_tag('img', attrs={'class': 'photo', 'style': 'width: 260px; height: 260px', 'src': 'photos/' + local_path.name})
                            photo_wrap_a.append(photo_img)
                            media_wrap_div.append(photo_wrap_a)
                            body_div.append(media_wrap_div)
                        elif predicate == 'messageMediaDocument':
                            mime = media['document']['mime_type'].content()
                            if mime == 'audio/ogg':
                                found = True
                                local_path = max(local_paths, key=lambda p: p.stat().st_size)
                                shutil.copy2(local_path, self.voice_messages_path)
                                media_voice_message_a = self.soup.new_tag('a', attrs={'class': ['media', 'clearfix', 'pull_left', 'block_link', 'media_voice_message'], 'href': 'voice_messages/' + local_path.name})
                                fill_div = self.soup.new_tag('div', attrs={'class': ['fill', 'pull_left']})
                                media_body_div = self.soup.new_tag('div', attrs={'class': 'body'})
                                title_div = self.soup.new_tag('div', attrs={'class': ['title', 'bold']})
                                title_div.string = f' Voice message '
                                
                                status_div = self.soup.new_tag('div', attrs={'class': ['status', 'details']})
                                duration = File(local_path).info.length
                                minutes = int(duration // 60)
                                seconds = int(duration % 60)
                                status_div.string = f' {minutes:02d}:{seconds:02d} '
                                
                                media_body_div.append(title_div)
                                media_body_div.append(status_div)
                                media_voice_message_a.append(fill_div)
                                media_voice_message_a.append(media_body_div)
                                media_wrap_div.append(media_voice_message_a)
                            elif mime == 'video/mp4':
                                if len(local_paths) >= 2:
                                    img_path = None
                                    video_path = None
                                    for p in local_paths:
                                        ext = p.suffix.lower()
                                        if ext in ('.jpg', '.jpeg', '.png'):
                                            img_path = p
                                        elif ext == '.mp4':
                                            video_path = p
                                    if video_path != None and img_path != None:
                                        found = True
                                        shutil.copy2(video_path, self.video_files_path)
                                        shutil.copy2(img_path, self.photos_path)
                                        video_file_wrap_a = self.soup.new_tag('a', attrs={'class': ['video_file_wrap', 'clearfix', 'pull_left'], 'href': 'video_files/' + video_path.name})
                                        video_play_bg_div = self.soup.new_tag('div', attrs={'class': 'video_play_bg'})
                                        video_play_div = self.soup.new_tag('div', attrs={'class': 'video_play'})
                                        video_duration_div = self.soup.new_tag('div', attrs={'class': 'video_duration'})
                                        video_file_img = self.soup.new_tag('img', attrs={'class': 'video_file', 'src': 'photos/' + img_path.name, 'style': 'width: 260px; height: 260px'})
                                        
                                        video_play_bg_div.append(video_play_div)
                                        video_file_wrap_a.append(video_play_bg_div)
                                        video_file_wrap_a.append(video_duration_div)
                                        video_file_wrap_a.append(video_file_img)
                                        media_wrap_div.append(video_file_wrap_a)
                            
                if not found:
                    media_wrap_div.string = ' (Media file not found) '
                body_div.append(media_wrap_div)
        if message_string:
            text_div = self.soup.new_tag('div', attrs={'class': 'text'})
            text_div.string = f' {message_string.content()} '
            body_div.append(text_div)
        if call:
            reason = call['action']['reason'].get_predicate()
            duration = None if call['action']['duration'] == None else call['action']['duration'].content()
            
            media_wrap_div = self.soup.new_tag('div', attrs={'class': ['media_wrap', 'clearfix']})
            media_div = self.soup.new_tag('div', attrs={'class': ['media', 'clearfix', 'pull_left', 'media_call']})
            fill_div = self.soup.new_tag('div', attrs={'class': ['fill', 'pull_left']})
            fill_div.string = ' '
            media_body_div = self.soup.new_tag('div', attrs={'class': 'body'})
            title_div = self.soup.new_tag('div', attrs={'class': ['title', 'bold']})
            status_div = self.soup.new_tag('div', attrs={'class': ['status', 'details']})
            
            if not call.is_set('out'):
                title_div.string = f' {self.self_name} '
                status_div.string = f' Incoming ({duration} seconds) '
            else:
                title_div.string = f' {self.dialog_name} '
                status_div.string = f' Outgoing ({duration} seconds) '
            
            if reason == 'phoneCallDiscardReasonMissed':
                status_div.string = ' Missed '
            elif reason == 'phoneCallDiscardReasonDisconnect':
                status_div.string = ' Disconnect '
            elif reason == 'phoneCallDiscardReasonBusy':
                status_div.string = ' Declined '
            elif reason == 'phoneCallDiscardReasonHangup':
                media_div['class'].append('success')
            
            media_body_div.append(title_div)
            media_body_div.append(status_div)
            media_div.append(fill_div)
            media_div.append(media_body_div)
            media_wrap_div.append(media_div)
            body_div.append(media_wrap_div)
            
        if post_author:
            signature_div = self.soup.new_tag('div', attrs={'class': ['signature', 'details']})
            signature_div.string = f' {post_author.content()} '
            body_div.append(signature_div)
                    
        message_div.append(body_div)
        self.history.append(message_div)
        
        self.last_date = date
        self.last_from_name = from_name
    def finish(self):
        self.file.write(str(self.soup))
        self.file.close()
    
    