"""試作HTMLへの追加(20261010-1925 作業7): 図鑑の研究メモ(data/lina_memos_100.csv)。1周目は「1周目の研究メモ」。エンディング後(2周目以降)は、取り消し線の部分に線を引き、訂正後(赤字)を続ける。1周目のメモは消さない。
make_prototype.py から apply(s)。適用済み(/* dan6:i */)なら飛ばす。入手した語だけ出す(未入手は出さない)。"""

JS = r'''// ===== 図鑑の研究メモ(20261010-1925 作業7) =====
const MEMOS=(CFG.PH&&CFG.PH.MEMOS)||null;
function memoHTML(n){
  if(!MEMOS||!MEMOS[n])return "";const m=MEMOS[n],after=lvOf(0)>=1,e=esc2;let h=e(m.memo);
  if(after){   // エンディング後: 取り消し線の部分に線を引き(メモの中に同じ文字列があれば、その部分。なければ、取り消し線つきで添える)、訂正後(赤字)を続ける
    const i=m.strike?m.memo.indexOf(m.strike):-1;
    h=i>=0?e(m.memo.slice(0,i))+'<s>'+e(m.strike)+'</s>'+e(m.memo.slice(i+m.strike.length)):e(m.memo)+(m.strike?' <s>'+e(m.strike)+'</s>':'');
    if(m.fix)h+=' <span class="red">'+e(m.fix)+'</span>';}
  return h;
}
function memoCard(n){const h=memoHTML(n);return '<div class="memo"><b>'+esc2(n)+'</b>'+(h?' <span class="mt">'+h+'</span>':'')+'</div>';}
'''
CSS = ".memo{margin:3px 0;line-height:1.6}.memo .mt{color:#44403a}.memo s{color:#8a8478}.memo .red{color:#d6336c;font-weight:700}\n"


def apply(s):
    if "/* dan6:i */" in s:
        return s

    def sub1(old, new):
        nonlocal s
        assert old in s, "dan6i パッチが当たらない: " + old[:70]
        s = s.replace(old, new, 1)

    sub1("function slotStats(){", JS + "function slotStats(){")
    sub1('${st.names[i].length?st.names[i].join("・"):"まだありません"}', '${st.names[i].length?st.names[i].map(memoCard).join(""):"まだありません"}')
    sub1(".sl-list{", CSS + ".sl-list{")
    s = s.replace("/* dan6:h */", "/* dan6:h *//* dan6:i */", 1)
    return s
