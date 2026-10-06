import csv,re,itertools,collections,random
R='/home/claude/mahjong-sim/'
W=list(csv.DictReader(open(R+'data/words_by_slot_v16.csv',encoding='utf-8-sig')))
MT=list(csv.DictReader(open(R+'data/modifier_triples_B.csv',encoding='utf-8-sig')))
HD=list(csv.DictReader(open(R+'dan5/heads.csv',encoding='utf-8-sig')))
RD={'見せ':'みせ','デカ':'でか','エロ':'えろ','舐め':'なめ','コキ':'こき','媚び':'こび','穴':'あな','ぬれ':'ぬれ','♡':'','×2':''}
def reading(name):
    name=name.split('・')[0]
    for k in sorted(RD,key=len,reverse=True): name=name.replace(k,RD[k])
    return name.replace('っ','つ').replace('ぉ゛','お')
# part rules (substring on first reading name)
PARTS=[('男性器',['ちんぽ','ちんこ','ちん']),
 ('女性器',['まんこ','おめこ','おまめ','まめ','まん','くり','ちつ','すじ']),
 ('胸',['ちくび','ぽっち','ぱい','おちち','ちち','ちく']),
 ('後ろ',['あなる','おけつ','うしろ','しっぽ','けつ','しり']),
 ('口',['くち','べろ'])]
def part_of(name,slot,sub):
    n=name.split('・')[0]
    if slot=='前置き': return ''
    if 'ちくコキ' in name: return '胸|口'
    if 'エロちく・エロくち' in name: return '胸|口'
    for p,keys in PARTS:
        for k in keys:
            if k in n: return p
    if re.search(r'あな|穴',n): return '穴'
    if n in('がんしゃ',): return '顔'
    return ''
SM=['まぞ','さど','どまぞ','しつけ','しかる','ぱちん']
def tone_of(name,slot,sub):
    n=name.split('・')[0]
    if slot=='前置き': return 'ラブ' if '♡' in n else '淫乱'
    if any(k in n for k in ['まぞ','さど','どまぞ']) or sub=='命令・誘い' or n in('しつけ','しかる','ぱちん','ぱんっ・ぱんつ'): return 'SM'
    if '♡' in n or any(k in n for k in ['すき','きす♡','まま','こびる','こびこび','めろめろ','きっす','べろちゅ']) or '媚び' in n: return 'ラブ'
    if slot=='喘ぎ声':
        return '淫乱' if any(k in n for k in ['おお','んお','うお','おう','おっ','おん','ぉ']) else ''
    if n in('すきすき',): return 'ラブ'
    if sub in('態度',) and n in('つんつん','いじいじ','おろおろ','おどおど','うじうじ','しめしめ'): return ''
    if sub=='感情・状況' and n in('がまん','じりっ'): return ''
    return '淫乱'
rows=[]
for r in W:
    rows.append(dict(word=r['word'],slot_no=int(r['slot_no']),slot=r['slot'],sub=r['sub'],kind='語'))
for r in MT:
    rows.append(dict(word=r['name'],slot_no=0,slot='前置き',sub='前置き',kind='語'))
for h in HD:
    t=h['type']
    if t=='喘ぎ声': rows.append(dict(word='【雀頭】'+h['head'],slot_no=6,slot='喘ぎ声',sub='雀頭・'+h['flavor'],kind='雀頭'))
    elif t=='快感': rows.append(dict(word='【雀頭】'+h['head'],slot_no=5,slot='反応',sub='雀頭・快感',kind='雀頭'))
    elif t=='擬音': rows.append(dict(word='【雀頭】'+h['head'],slot_no=4,slot='音',sub='雀頭・擬音',kind='雀頭'))
    else: rows.append(dict(word='【雀頭】'+h['head'],slot_no=2,slot='部位',sub='雀頭・略称('+h['note']+')',kind='雀頭',_part=h['stem'],_flv=h['flavor']))
rows.append(dict(word='【雀頭】しり',slot_no=2,slot='部位',sub='雀頭・略称(追加)',kind='雀頭',_part='しり',_flv='後ろ'))
for r in rows:
    nm=r['word'].replace('【雀頭】','')
    r['reading']=reading(nm)
    if r['kind']=='雀頭' and '略称' in r['sub']:
        r['part']=r['_flv'] if r['_flv'] in('男性器','女性器','胸','後ろ','口') else ''
        r['tone']='SM' if r['_flv']=='SM' else ('' if r['_flv']=='役割' else '淫乱')
        r['slot_no_eff']=6   # 雀頭は一行の最後
    elif r['kind']=='雀頭':
        r['part']=''
        r['tone']='淫乱' if ('オホ' in r['sub']) else ''
        if r['sub']=='雀頭・快感': r['tone']='淫乱'
        if r['sub']=='雀頭・擬音': r['tone']='淫乱'
        r['slot_no_eff']=r['slot_no']
    else:
        r['part']='' if r['slot']=='音' else part_of(r['word'],r['slot'],r['sub'])
        r['tone']=tone_of(r['word'],r['slot'],r['sub'])
        r['slot_no_eff']=r['slot_no']
if __name__=='__main__':
    print(len(rows))
    c=collections.Counter((r['slot'],r['part']) for r in rows if r['kind']=='語')
    for k,v in sorted(c.items()): print(k,v)
    print(collections.Counter(r['tone'] for r in rows))
    for r in rows:
        if r['slot'] in('部位','行為','反応','感情・誘い') and r['part']=='' and r['kind']=='語': print('部位なし',r['slot'],r['sub'],r['word'],end=' | ')
