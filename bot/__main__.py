import os
import sqlite3
from pyrogram import filters
from bot import LOG, app, advance_config, chats_data, from_chats, to_chats, \
                remove_strings, replace_string, sudo_users


#init sqlite
conn = sqlite3.connect('messages.sqlite', check_same_thread=False)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS Messages (original_chat LONG, original_id LOGN, dest_chat LONG, dest_id LONG)')
conn.commit()

def put_dest_id(original_chat, original_id, dest_chat, dest_id):
  cur.execute('INSERT INTO Messages values (?, ?, ?, ?)', (original_chat, original_id, dest_chat, dest_id))
  conn.commit()

def get_dest_id(original_chat, original_id, dest_chat):
  cur.execute('SELECT dest_id FROM Messages WHERE original_chat = ? AND original_id = ? AND dest_chat = ?', (original_chat, original_id, dest_chat))
  data = cur.fetchall()
  if len(data) > 0:
    return data[0][0]
  return None

def is_supported_media(message):
  return message.media and (message.audio or message.photo or message.document or message.video or message.voice)


def copy_with_media(client, message, to):
  
  old_message = None
  new_message = None
  
  # это отредактированое сообщение? (пока не умеем заменять картинку и файл в сообщениях, а так же изменять только форматирование, без текста!)
  dest_id = get_dest_id(message.chat.id, message.message_id, to)
  if dest_id:
    old_message = client.get_messages(to, dest_id)

  if old_message:
    if is_supported_media(message):
      if old_message.caption != message.caption:
        client.edit_message_caption(chat_id=to, message_id=old_message.message_id, caption=message.caption, caption_entities=message.caption_entities)
    else:
      if old_message.text != message.text:
        old_message.edit(text=message.text, entities=message.entities)
  
  # или это новое сообщение?
  else: 

    replay_id = None
    
    # это replay?
    if message.reply_to_message:
      replay_id = get_dest_id(message.chat.id, message.reply_to_message.message_id, to)

    if is_supported_media(message):
      file = message.download('/tmp/tgfiles/')
      if message.photo:
        new_message = client.send_photo(chat_id=to, photo=file, caption=message.caption, caption_entities=message.caption_entities, reply_to_message_id=replay_id)
      else:
        new_message = client.send_document(chat_id=to, document=file, caption=message.caption, caption_entities=message.caption_entities, reply_to_message_id=replay_id)
      os.remove(file)
    else:
      new_message = client.send_message(chat_id=to, text=message.text, entities=message.entities, reply_to_message_id=replay_id)
      
  if new_message:
    put_dest_id(message.chat.id, message.message_id, to, new_message.message_id)

@app.on_message(filters.chat(from_chats) & filters.incoming)
def work(client, message):
  try:
    for chat in to_chats:
      copy_with_media(client, message, chat)
  except Exception as e:
    LOG.error(e)

app.run()
