"""Shared deterministic Chinese spoken-form normalization, applied AFTER tool parsing.
Never use this function to change tool arguments or to supply a transcript to Edge.
"""
import re,unicodedata
VERSION='zh_spoken_v1'
DIGITS='零一二三四五六七八九'
def digits(s):return ''.join(DIGITS[int(c)] if c.isdigit() and c.isascii() else c for c in s)
def integer(n):
    n=int(n)
    if n<0:return '负'+integer(-n)
    if n==0:return '零'
    def section(x):
        result='';zero=False
        for power,unit in [(1000,'千'),(100,'百'),(10,'十'),(1,'')]:
            q,x=divmod(x,power)
            if q:
                if zero and result:result+='零'
                result+=DIGITS[q]+unit;zero=False
            elif result and x:zero=True
        return result
    groups=[]
    while n:groups.append(n%10000);n//=10000
    if len(groups)>4:return digits(str(sum(g*10000**i for i,g in enumerate(groups))))
    out='';gap=False
    for i in range(len(groups)-1,-1,-1):
        v=groups[i]
        if not v:
            if out:gap=True
            continue
        if out and (gap or v<1000):out+='零'
        out+=section(v)+['','万','亿','万亿'][i];gap=False
    return out[1:] if out.startswith('一十') else out
def number(value):
    value=value.replace(',','')
    sign='负' if value.startswith('-') else '正' if value.startswith('+') else ''
    value=value.lstrip('+-')
    if '.' in value:
        left,right=value.split('.',1);return sign+integer(left or '0')+'点'+digits(right)
    if len(value)>1 and value.startswith('0'):return sign+digits(value)
    return sign+integer(value)
def clock(h,m,s=None):
    h,m=int(h),int(m)
    if h>23 or m>59 or s and int(s)>59:return None
    out=integer(h)+'点'
    if m:out+=integer(m)+'分'
    if s and int(s):out+=(('零分' if m==0 else '')+integer(int(s))+'秒')
    elif not m:out+='整'
    return out
NUM=r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
UNITS={'℃':'摄氏度','°C':'摄氏度','°c':'摄氏度','°F':'华氏度','℉':'华氏度','kWh':'千瓦时','kW':'千瓦','Wh':'瓦时','W':'瓦',
 'μg/m³':'微克每立方米','µg/m³':'微克每立方米','mg/m³':'毫克每立方米','km²':'平方千米','cm²':'平方厘米','m²':'平方米','m³':'立方米',
 'mL':'毫升','ml':'毫升','L':'升','kg':'千克','mg':'毫克','g':'克','km':'千米','cm':'厘米','mm':'毫米','m':'米','Hz':'赫兹','kHz':'千赫兹','MHz':'兆赫兹','GHz':'吉赫兹','K':'开尔文','lx':'勒克斯','lux':'勒克斯','dB':'分贝','ms':'毫秒','s':'秒','min':'分钟','h':'小时','V':'伏','A':'安','°':'度'}
def normalize(text):
    text=str(text).strip().translate(str.maketrans('０１２３４５６７８９％：．－＋','0123456789%:.-+'))
    text=text.replace('CO₂','二氧化碳').replace('CO2','二氧化碳').replace('PM2.5','细颗粒物')
    # ISO date/time: dates precede signs/ranges so hyphens cannot become negatives.
    def iso(m):
        y,mo,d,h,mi,s,zone=m.groups();spoken=digits(y)+'年'+integer(mo)+'月'+integer(d)+'日'+(clock(h,mi,s) or m.group(0))
        if zone in ('+08:00','+0800'):spoken+='，东八区'
        elif zone=='Z':spoken+='，协调世界时'
        elif zone:spoken+='，时区偏移'+('正' if zone[0]=='+' else '负')+integer(zone[1:3])+'小时'+(integer(zone[-2:])+'分钟' if int(zone[-2:]) else '')
        return spoken
    text=re.sub(r'\b(\d{4})-(\d{2})-(\d{2})[T ](\d{1,2}):(\d{2})(?::(\d{2}))?(Z|[+-]\d{2}:?\d{2})?',iso,text)
    text=re.sub(r'(?<!\d)(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?',lambda m:digits(m[1])+'年'+integer(m[2])+'月'+integer(m[3])+'日',text)
    text=re.sub(r'(?<!\d)(\d{4})年',lambda m:digits(m[1])+'年',text)
    text=re.sub(r'(?<!\d)(\d{1,2}):(\d{2})(?::(\d{2}))?(?!\d)',lambda m:clock(m[1],m[2],m[3]) or m[0],text)
    # Preserve literal identity for phone-like long digit sequences and identifiers.
    text=re.sub(r'(?<!\d)1\d{10}(?!\d)',lambda m:digits(m[0]),text)
    text=re.sub(r'(?i)\b(?:[a-z]+[_-])+(?:[a-z0-9_-]+)\b',lambda m:re.sub(r'\d+',lambda k:digits(k[0]),m[0]).replace('_',' ').replace('-',' '),text)
    text=re.sub(r'('+NUM+r')\s*(?:~|～|–|—|至|到|(?<=\d)-)(?=\d)',lambda m:number(m[1])+'到',text)
    text=re.sub(r'('+NUM+r')\s*%',lambda m:'百分之'+number(m[1]),text)
    text=re.sub(r'('+NUM+r')\s*‰',lambda m:'千分之'+number(m[1]),text)
    text=re.sub(r'('+NUM+r')\s*ppm\b',lambda m:'百万分之'+number(m[1]),text,flags=re.I)
    unit_pattern='|'.join(re.escape(k) for k in sorted(UNITS,key=len,reverse=True))
    text=re.sub(r'('+NUM+r')\s*('+unit_pattern+r')(?![A-Za-z])',lambda m:number(m[1])+UNITS[m[2]],text)
    text=text.replace('℃','摄氏度').replace('°C','摄氏度').replace('℉','华氏度')
    text=re.sub(NUM,lambda m:number(m[0]),text)
    return text
def record(text):return {'normalizer_version':VERSION,'raw_text':text,'spoken_text':normalize(text)}
