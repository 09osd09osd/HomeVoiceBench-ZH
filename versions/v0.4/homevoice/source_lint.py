"""Reject implementation identifiers in natural household user speech."""
import re
FIELD_WORDS=['mode','power','brightness_pct','color_temperature_k','target_temperature_c','opening_pct','volume_pct','fan_speed','device_id','room_id','device_query','device_set','sensor_read','schedule_list','schedule_create','schedule_update','schedule_cancel','media_search','media_play','media_control','task_get','task_cancel','auto','sleep','manual']
PATTERN=re.compile(r'(?<![A-Za-z0-9_])(?:'+'|'.join(map(re.escape,FIELD_WORDS))+r')(?![A-Za-z0-9_])',re.I)
NATURAL={'brightness_pct':'亮度','color_temperature_k':'色温','target_temperature_c':'设定温度','opening_pct':'打开比例','volume_pct':'音量','fan_speed':'风速档位','mode':'运行模式','power':'开关','auto':'自动','sleep':'睡眠','manual':'手动'}

def naturalize(text):
    # Only prose changes; numeric targets and executable tool arguments stay intact.
    text=re.sub(r'[（(]sleep=睡眠[，,]\s*manual=手动[，,]\s*auto=自动[）)]','',text)
    for word,chinese in NATURAL.items():
        text=re.sub(r'(?<![A-Za-z0-9_])'+re.escape(word)+r'(?![A-Za-z0-9_])',chinese,text)
    return text
def issues(text,category):
    if category!='tool':return []
    return sorted(set(PATTERN.findall(text)))
