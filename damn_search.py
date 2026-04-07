import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import urllib.request
import urllib.parse
import re
import concurrent.futures

class DamnSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DamnSearch - 英语题目溯源工具 🔍 (v2.0 并发智能版)")
        self.root.geometry("900x800")
        self.root.minsize(700, 500)
        
        self.executor = None
        self.create_widgets()
        
    def create_widgets(self):
        # 1. 顶部操作区
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(top_frame, text="第1步:").pack(side=tk.LEFT)
        self.extract_btn = ttk.Button(top_frame, text="✨ 智能清洗/提取题目", command=self.smart_extract)
        self.extract_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(top_frame, text=" |   第2步:").pack(side=tk.LEFT, padx=5)
        ttk.Label(top_frame, text="并行数量(建议10-30):").pack(side=tk.LEFT)
        self.workers_var = tk.IntVar(value=20)
        self.workers_spin = ttk.Spinbox(top_frame, from_=1, to=50, width=5, textvariable=self.workers_var)
        self.workers_spin.pack(side=tk.LEFT, padx=5)
        
        self.search_btn = ttk.Button(top_frame, text="🚀 开始并行溯源", command=self.start_search)
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(top_frame, text="🗑️ 清空面板", command=self.clear_all)
        self.clear_btn.pack(side=tk.RIGHT, padx=5)
        
        # 使用 PanedWindow 实现上下拖拽风格
        paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 2. 输入区
        input_frame = ttk.LabelFrame(paned, text=" 📝 原始数据粘贴区 (请直接复制整个题库网页粘贴到这里)")
        paned.add(input_frame, weight=1)
        
        self.input_text = scrolledtext.ScrolledText(input_frame, height=10, font=("Consolas", 10))
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.input_text.insert(tk.END, "如果你有测试题集，直接从网页 Ctrl+C 复制粘贴过来，哪怕混杂着选项ABCD、分数、页面标题也无所谓。\n\n贴好后，点击上方的【✨ 智能清洗/提取题目】即可自动抽提出干干净净的纯英文题干列表！")
        
        # 3. 输出结果区
        output_frame = ttk.LabelFrame(paned, text=" 🎯 溯源及匹配结果 (并行检索会无序返回，请注意题号)")
        paned.add(output_frame, weight=3)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4")
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("状态: 准备就绪")
        status_label = ttk.Label(self.root, textvariable=self.status_var, font=("微软雅黑", 9, "bold"))
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

    def smart_extract(self):
        raw_text = self.input_text.get(1.0, tk.END)
        # 精准匹配：“数字.”开头，然后紧跟英文字符（防止提取到如 2026.04.07 这样的日期时间行）
        pattern = re.compile(r'^\s*\d+[\.、]\s*([A-Za-z].*)', re.MULTILINE)
        matches = pattern.findall(raw_text)
        
        if matches:
            cleaned = "\n".join(matches)
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, cleaned)
            self.status_var.set(f"状态: ✨ 智能提取成功！剔除了所有网页垃圾字和ABCD选项，共提取出 {len(matches)} 道纯英文题干。")
        else:
            # 兜底通用去噪：基于行长和黑名单剔除
            lines = raw_text.split('\n')
            valid_lines = []
            for line in lines:
                line = line.strip()
                if not line: continue
                # 屏蔽常见的ABC选项
                if re.match(r'^(A|B|C|D|E|F)[\.、]?$', line, re.IGNORECASE): continue
                # 屏蔽分数和网页UI元素
                if line in ['单选题', '多选题', '已答', '未答', '答题卡'] or '分)' in line or line == '分': continue
                if len(line) < 10: continue
                valid_lines.append(line)
            
            cleaned = "\n".join(valid_lines)
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, cleaned)
            self.status_var.set("状态: ⚠️ 网页内未发现标准带序号(1. 2.)的题目，触发通用去噪过滤，请手动检查列表格式。")

    def clear_all(self):
        self.input_text.delete(1.0, tk.END)
        self.output_text.delete(1.0, tk.END)
        self.status_var.set("状态: 已清空面板")
        
    def append_output(self, text):
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        
    def start_search(self):
        raw_text = self.input_text.get(1.0, tk.END)
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        if not lines:
            self.status_var.set("状态: ❌ 请先填入清洗后的英文题库！")
            return
            
        self.output_text.delete(1.0, tk.END)
        self.search_btn.config(state=tk.DISABLED)
        self.extract_btn.config(state=tk.DISABLED)
        
        workers = self.workers_var.get()
        self.status_var.set(f"状态: 🔍 正在满载并发检索 {len(lines)} 道题...")
        
        self.completed_count = 0
        self.total_lines = len(lines)
        threading.Thread(target=self.run_batch_search, args=(lines, workers), daemon=True).start()

    def run_batch_search(self, lines, workers):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        
        future_map = {self.executor.submit(self.search_bing, f'"{line}"'): (idx+1, line) for idx, line in enumerate(lines)}
        
        for future in concurrent.futures.as_completed(future_map):
            idx, line = future_map[future]
            try:
                results = future.result()
                self.root.after(0, self.update_result_ui, idx, line, results)
            except Exception as exc:
                self.root.after(0, self.update_result_ui, idx, line, [f"网络异常/拦截: {exc}"])

        self.executor.shutdown(wait=True)
        self.root.after(0, self.finish_search)

    def update_result_ui(self, idx, line, results):
        self.completed_count += 1
        out_str = f"=========================================\n🔎 【第 {idx} 题】 {line}\n"
        if not results:
            out_str += "   ❌ 未能找到题目出处。\n"
        else:
            for i, res in enumerate(results):
                snippet = re.sub(r'\s+', ' ', res)[:300]
                out_str += f"   ✅ [来源摘要 {i+1}]: {snippet}...\n"
                
        self.append_output(out_str)
        self.status_var.set(f"状态: 🔍 并发加速检索中...进度 ({self.completed_count}/{self.total_lines})")

    def finish_search(self):
        self.search_btn.config(state=tk.NORMAL)
        self.extract_btn.config(state=tk.NORMAL)
        self.status_var.set(f"状态: ✨ 全力全开！{self.total_lines} 道题目检索全部结束！")

    def search_bing(self, query, top_n=3):
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        })
        try:
            html = urllib.request.urlopen(req, timeout=12).read().decode('utf-8')
            results = set(re.findall(r'<div class="b_caption".*?>(.*?)</div>', html, re.IGNORECASE | re.DOTALL))
            clean_results = [re.sub(r'<[^>]+>', '', res).strip() for res in list(results)]
            if not clean_results: return []
            return clean_results[:top_n]
        except Exception as e:
            return [f"搜索被拦截或超时: {e}"]

if __name__ == "__main__":
    root = tk.Tk()
    app = DamnSearchApp(root)
    root.mainloop()
