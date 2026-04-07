import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import urllib.request
import urllib.parse
import re

class DamnSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DamnSearch - 英语题目溯源工具 🔍")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        self.create_widgets()
        
    def create_widgets(self):
        # 1. 顶部提示与输入区
        input_frame = ttk.LabelFrame(self.root, text=" 📝 请在此处粘贴你要查询的英文题目 (每行一题) ")
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.input_text = scrolledtext.ScrolledText(input_frame, height=8, font=("Consolas", 10))
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.input_text.insert(tk.END, "The dark clouds suggest a(n) _______ storm.\nJohn was confined to bed for a week with his bad cold.")
        
        # 2. 控制按钮区
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.search_btn = ttk.Button(btn_frame, text="🚀 一键无情查题 (Search)", command=self.start_search)
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(btn_frame, text="🗑️ 清空所有 (Clear)", command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("状态: 等待中...")
        status_label = ttk.Label(btn_frame, textvariable=self.status_var, font=("微软雅黑", 9, "bold"))
        status_label.pack(side=tk.RIGHT, padx=5)

        # 3. 底部输出结果区
        output_frame = ttk.LabelFrame(self.root, text=" 🎯 溯源及匹配结果 ")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4")
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def clear_all(self):
        self.input_text.delete(1.0, tk.END)
        self.output_text.delete(1.0, tk.END)
        self.status_var.set("状态: 已清空")
        
    def append_output(self, text):
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        
    def start_search(self):
        # 获取输入内容
        raw_text = self.input_text.get(1.0, tk.END)
        lines = [line.strip() for line in raw_text.split('\n') if line.strip() and not line.strip().startswith(('A.', 'B.', 'C.', 'D.'))]
        
        if not lines:
            self.status_var.set("状态: ❌ 请输入有效题目！")
            return
            
        self.output_text.delete(1.0, tk.END)
        self.search_btn.config(state=tk.DISABLED)
        self.status_var.set(f"状态: 🔍 正在检索 {len(lines)} 道题...")
        
        # 开启子线程防止界面卡死
        threading.Thread(target=self.run_search_thread, args=(lines,), daemon=True).start()

    def run_search_thread(self, lines):
        for index, line in enumerate(lines, 1):
            self.append_output(f"=========================================\n🔎 【第 {index} 题】 {line}")
            results = self.search_bing(f'"{line}"')
            
            if not results:
                self.append_output("   ❌ 未能在搜索引擎中找到精确匹配的题目来源。\n")
            else:
                for i, res in enumerate(results):
                    snippet = re.sub(r'\s+', ' ', res)[:300]
                    self.append_output(f"   ✅ [来源摘要 {i+1}]: {snippet}...\n")
            
            # 更新状态栏进度
            self.root.after(0, lambda idx=index, total=len(lines): self.status_var.set(f"状态: 🔍 进度 {idx}/{total}"))
            
        self.root.after(0, self.finish_search)
        
    def finish_search(self):
        self.search_btn.config(state=tk.NORMAL)
        self.status_var.set("状态: ✨ 检索全部完成！")

    def search_bing(self, query, top_n=3):
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
        })
        try:
            html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
            # 提取Bing搜索结果摘要
            results = set(re.findall(r'<div class="b_caption".*?>(.*?)</div>', html, re.IGNORECASE | re.DOTALL))
            clean_results = [re.sub(r'<[^>]+>', '', res).strip() for res in list(results)]
            return clean_results[:top_n]
        except Exception as e:
            return [f"搜索遇到网络错误或拦截: {e}"]

if __name__ == "__main__":
    root = tk.Tk()
    app = DamnSearchApp(root)
    root.mainloop()
