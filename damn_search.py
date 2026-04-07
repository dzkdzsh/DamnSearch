import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import urllib.request
import urllib.parse
import re
import concurrent.futures
from collections import Counter

class DamnSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DamnSearch - 英语题目智能溯源及搜题器 🔍 (v3.0 终极版)")
        self.root.geometry("900x800")
        self.root.minsize(700, 500)
        
        self.executor = None
        self.answers_dict = {}
        self.create_widgets()
        
    def create_widgets(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(top_frame, text="第1步:").pack(side=tk.LEFT)
        self.extract_btn = ttk.Button(top_frame, text="✨ 智能清洗/提取题目", command=self.smart_extract)
        self.extract_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(top_frame, text=" |   第2步:").pack(side=tk.LEFT, padx=5)
        ttk.Label(top_frame, text="并行数量(建议10+):").pack(side=tk.LEFT)
        self.workers_var = tk.IntVar(value=10)
        self.workers_spin = ttk.Spinbox(top_frame, from_=1, to=50, width=5, textvariable=self.workers_var)
        self.workers_spin.pack(side=tk.LEFT, padx=5)
        
        self.search_btn = ttk.Button(top_frame, text="🚀 开始溯源寻解", command=self.start_search)
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(top_frame, text="🗑️ 清空面板", command=self.clear_all)
        self.clear_btn.pack(side=tk.RIGHT, padx=5)
        
        paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        input_frame = ttk.LabelFrame(paned, text=" 📝 原始数据粘贴区 (连网页垃圾一起粘贴)")
        paned.add(input_frame, weight=1)
        
        self.input_text = scrolledtext.ScrolledText(input_frame, height=10, font=("Consolas", 10))
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.input_text.insert(tk.END, "")
        
        output_frame = ttk.LabelFrame(paned, text=" 🎯 溯源及匹配结果 (执行完毕附带答案速览)")
        paned.add(output_frame, weight=3)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4")
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("状态: 准备就绪")
        status_label = ttk.Label(self.root, textvariable=self.status_var, font=("微软雅黑", 9, "bold"))
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

    def smart_extract(self):
        raw_text = self.input_text.get(1.0, tk.END)
        # 精确正则匹配真实题号（如 1.I have been...）
        pattern = re.compile(r'^\s*\d+[\.、]\s*([A-Za-z].*)', re.MULTILINE)
        matches = pattern.findall(raw_text)
        
        if matches:
            cleaned = "\n".join(matches)
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, cleaned)
            self.status_var.set(f"状态: ✨ 智能提取成功！剔除了所有ABCD选项及网页打分等杂质，共提取 {len(matches)} 道纯题干。")
        else:
            self.status_var.set("状态: ❌ 提取失败，剪贴板文本中未发现标准格式（数字.字母）题干。")

    def clear_all(self):
        self.input_text.delete(1.0, tk.END)
        self.output_text.delete(1.0, tk.END)
        self.status_var.set("状态: 已清空")
        
    def append_output(self, text):
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        
    def start_search(self):
        raw_text = self.input_text.get(1.0, tk.END)
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        if not lines:
            self.status_var.set("状态: ❌ 请先填入清洗后的题库！")
            return
            
        self.output_text.delete(1.0, tk.END)
        self.search_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.DISABLED)
        
        # 重置答案记录
        self.answers_dict = {}
        
        workers = self.workers_var.get()
        self.status_var.set(f"状态: 🔍 正在并发溯源寻找答案... (共 {len(lines)} 题)")
        
        self.completed_count = 0
        self.total_lines = len(lines)
        threading.Thread(target=self.run_batch_search, args=(lines, workers), daemon=True).start()

    def run_batch_search(self, lines, workers):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        future_map = {self.executor.submit(self.search_bing, line): (idx+1, line) for idx, line in enumerate(lines)}
        
        for future in concurrent.futures.as_completed(future_map):
            idx, line = future_map[future]
            try:
                results, best_guess = future.result()
                self.answers_dict[idx] = best_guess
                self.root.after(0, self.update_result_ui, idx, line, results, best_guess)
            except Exception as exc:
                self.answers_dict[idx] = "?"
                self.root.after(0, self.update_result_ui, idx, line, [f"异常: {exc}"], "?")

        self.executor.shutdown(wait=True)
        self.root.after(0, self.finish_search)

    def update_result_ui(self, idx, line, results, best_guess):
        self.completed_count += 1
        out_str = f"=========================================\n🔎 【第 {idx} 题】 {line}\n"
        out_str += f"   💡 【AI机器预测答案】: {best_guess}\n"
        if not results:
            out_str += "   ❌ 溯源摘要: 未找到相关页面。\n"
        else:
            for i, res in enumerate(results):
                snippet = re.sub(r'\s+', ' ', res)[:200]
                out_str += f"   ✅ [来源 {i+1}]: {snippet}...\n"
                
        self.append_output(out_str)
        self.status_var.set(f"状态: 🔍 寻找答案进度 ({self.completed_count}/{self.total_lines}) ...")

    def finish_search(self):
        self.search_btn.config(state=tk.NORMAL)
        self.extract_btn.config(state=tk.NORMAL)
        
        # 集中输出答案表
        self.append_output("\n" + "🎊"*5 + "【 本次查题预测答案速览 】" + "🎊"*5)
        ans_lines = []
        for idx in sorted(self.answers_dict.keys()):
            ans_lines.append(f" 第 {idx:02d} 题 : {self.answers_dict[idx]} ")
        
        # 分两列排版
        for i in range(0, len(ans_lines), 2):
            line_str = ans_lines[i]
            if i + 1 < len(ans_lines):
                line_str += "  ||  " + ans_lines[i+1]
            self.append_output(line_str)
            
        self.append_output("-" * 50)
        self.append_output("*注: 答案通过抓取高频题库页面中的关键字[答案XX]得出, 个别无数据题可能显示为 ? 。仅供参考！")
            
        self.status_var.set("状态: ✨ 溯源与答案搜集全部完毕！请拉到底部保存答案。")

    def search_bing(self, query, top_n=3):
        # 优化搜索1：移除 ____ 下横线和标点，极大提升Bing的词组命中率，解决“溯源少或不准确”的痛点
        clean_query = re.sub(r'_{2,}', ' ', query).strip()
        # 将搜索关键字进行URL编码，注意不直接加上双引号来增强长句纠错和容错率
        url = f"https://www.bing.com/search?q={urllib.parse.quote(clean_query)}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        })
        try:
            html = urllib.request.urlopen(req, timeout=12).read().decode('utf-8')
            
            # 从 HTML 中强制剥离出纯文本（剔除冗长的Tag进行正则匹配寻找答案ABCD）
            pure_text = re.sub(r'<[^>]+>', ' ', html)
            # 在全页面寻找“答案: A”, “正确选项 D”字眼
            ans_patterns = re.findall(r'(?:【答案】|答案[：:]?\s*|正确选项\s*[：:]?\s*|正确答案\s*[：:]?\s*|参考答案\s*[：:]?\s*)([A-D])', pure_text, re.IGNORECASE)
            
            if ans_patterns:
                # 若页面多次提及，找最频繁出现的那一个选项
                guessed_ans = Counter(ans_patterns).most_common(1)[0][0].upper()
            else:
                guessed_ans = "?"
                
            # 获取检索摘要来源展示
            raw_results = set(re.findall(r'<div class="b_caption".*?>(.*?)</div>', html, re.IGNORECASE | re.DOTALL))
            clean_results = [re.sub(r'<[^>]+>', '', res).strip() for res in list(raw_results)]
            
            return clean_results[:top_n], guessed_ans
        except Exception as e:
            return [], "?"

if __name__ == "__main__":
    root = tk.Tk()
    app = DamnSearchApp(root)
    root.mainloop()
