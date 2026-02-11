import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import re

# YouTube Raw Data - 60 FPS Frame to Millisecond Mapping
# DO NOT CALCULATE - Use this exact mapping to prevent 1-frame drift
FRAME_MAP = {
    0: "016", 1: "032", 2: "048", 3: "064", 4: "080",
    5: "096", 6: "111", 7: "127", 8: "143", 9: "159",
    10: "175", 11: "191", 12: "206", 13: "222", 14: "238",
    15: "254", 16: "270", 17: "286", 18: "301", 19: "317",
    20: "350", 21: "366", 22: "381", 23: "397", 24: "413",
    25: "429", 26: "445", 27: "461", 28: "476", 29: "492",
    30: "508", 31: "524", 32: "540", 33: "556", 34: "571",
    35: "587", 36: "603", 37: "619", 38: "635", 39: "651",
    40: "683", 41: "699", 42: "715", 43: "731", 44: "746",
    45: "762", 46: "778", 47: "794", 48: "810", 49: "826",
    50: "841", 51: "857", 52: "873", 53: "889", 54: "905",
    55: "921", 56: "936", 57: "952", 58: "968", 59: "984"
}


def convert_timecode(hh, mm, ss, ff):
    """
    Convert HH:MM:SS:FF to HH:MM:SS,mmm format using YouTube's exact frame mapping.
    
    Args:
        hh, mm, ss, ff: Hour, Minute, Second, Frame values
    
    Returns:
        Tuple of (hours, minutes, seconds, milliseconds_string)
    """
    # Handle frame overflow (60+ frames)
    extra_seconds, frame = divmod(ff, 60)
    ss += extra_seconds
    
    # Handle second overflow
    extra_minutes, ss = divmod(ss, 60)
    mm += extra_minutes
    
    # Handle minute overflow
    extra_hours, mm = divmod(mm, 60)
    hh += extra_hours
    
    # Get milliseconds from the frame map (YouTube Raw Data)
    milliseconds = FRAME_MAP.get(frame, "000")
    
    return hh, mm, ss, milliseconds


def format_srt_time(hh, mm, ss, ms):
    """Format time for SRT: HH:MM:SS,mmm"""
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms}"


def format_sbv_time(hh, mm, ss, ms):
    """Format time for SBV: H:MM:SS.mmm"""
    return f"{hh}:{mm:02d}:{ss:02d}.{ms}"


def parse_input_text(text):
    """
    Parse input text and extract timecode ranges with subtitle content.
    
    Expected format:
    HH:MM:SS:FF - HH:MM:SS:FF
    Subtitle text here
    
    Returns:
        List of tuples: [(start_time, end_time, subtitle_text), ...]
    """
    # Pattern to match timecode range: HH:MM:SS:FF - HH:MM:SS:FF
    pattern = r'(\d{1,2}):(\d{2}):(\d{2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2}):(\d{2}):(\d{2})'
    
    lines = text.strip().split('\n')
    subtitles = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(pattern, line)
        
        if match:
            # Extract start and end timecodes
            start_hh, start_mm, start_ss, start_ff = map(int, match.groups()[:4])
            end_hh, end_mm, end_ss, end_ff = map(int, match.groups()[4:])
            
            # Collect subtitle text (lines after timecode until next timecode or end)
            subtitle_lines = []
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if re.match(pattern, next_line):
                    break
                if next_line:  # Only add non-empty lines
                    subtitle_lines.append(next_line)
                i += 1
            
            subtitle_text = '\n'.join(subtitle_lines)
            
            if subtitle_text:  # Only add if there's actual subtitle text
                subtitles.append((
                    (start_hh, start_mm, start_ss, start_ff),
                    (end_hh, end_mm, end_ss, end_ff),
                    subtitle_text
                ))
        else:
            i += 1
    
    return subtitles


def convert_to_srt(subtitles):
    """Convert parsed subtitles to SRT format"""
    output = []
    
    for idx, (start, end, text) in enumerate(subtitles, 1):
        start_time = format_srt_time(*convert_timecode(*start))
        end_time = format_srt_time(*convert_timecode(*end))
        
        output.append(f"{idx}")
        output.append(f"{start_time} --> {end_time}")
        output.append(text)
        output.append("")  # Empty line between subtitles
    
    return '\n'.join(output)


def convert_to_sbv(subtitles):
    """Convert parsed subtitles to SBV format"""
    output = []
    
    for start, end, text in subtitles:
        start_time = format_sbv_time(*convert_timecode(*start))
        end_time = format_sbv_time(*convert_timecode(*end))
        
        output.append(f"{start_time},{end_time}")
        output.append(text)
        output.append("")  # Empty line between subtitles
    
    return '\n'.join(output)


class SubtitleConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("유튜브 전용 60 FPS 자막 변환기")
        self.root.geometry("1400x750")
        
        # Store last converted results
        self.last_srt_result = ""
        self.last_sbv_result = ""
        
        # Title
        title_label = tk.Label(
            root, 
            text="유튜브 전용 60 FPS 자막 변환기",
            font=("맑은 고딕", 16, "bold"),
            pady=10
        )
        title_label.pack()
        
        # Instruction
        instruction_text = (
            "입력 형식: HH:MM:SS:FF - HH:MM:SS:FF (다음 줄에 자막 내용 입력)"
        )
        instruction_label = tk.Label(
            root,
            text=instruction_text,
            font=("맑은 고딕", 9),
            fg="gray"
        )
        instruction_label.pack()
        
        # Main container with 3 columns
        main_container = tk.Frame(root)
        main_container.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # LEFT: Input frame
        input_frame = tk.Frame(main_container, relief=tk.RIDGE, borderwidth=2, width=500)
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        input_frame.pack_propagate(False)
        
        input_header = tk.Frame(input_frame)
        input_header.pack(fill=tk.X, padx=5, pady=5)
        
        input_label = tk.Label(
            input_header, 
            text="📝 입력", 
            font=("맑은 고딕", 11, "bold")
        )
        input_label.pack(side=tk.LEFT)
        
        load_file_button = tk.Button(
            input_header,
            text="📂 TXT 파일 열기",
            command=self.load_file,
            font=("맑은 고딕", 9),
            bg="#9C27B0",
            fg="white",
            padx=10,
            pady=3
        )
        load_file_button.pack(side=tk.RIGHT)
        
        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            bg="#f9f9f9"
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # CENTER: Output frame
        output_frame = tk.Frame(main_container, relief=tk.RIDGE, borderwidth=2, width=500)
        output_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        output_frame.pack_propagate(False)
        
        output_label = tk.Label(
            output_frame, 
            text="📤 출력 결과", 
            font=("맑은 고딕", 11, "bold")
        )
        output_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            bg="#f0f8ff"
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # RIGHT: Button frame (vertical)
        button_frame = tk.Frame(main_container, relief=tk.RIDGE, borderwidth=2, width=180)
        button_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
        button_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        button_label = tk.Label(
            button_frame,
            text="⚙️ 변환",
            font=("맑은 고딕", 11, "bold")
        )
        button_label.pack(pady=(10, 15))
        
        # Vertical button layout
        srt_button = tk.Button(
            button_frame,
            text="SRT 변환",
            command=self.convert_srt,
            font=("맑은 고딕", 10, "bold"),
            bg="#4CAF50",
            fg="white",
            width=15,
            height=2
        )
        srt_button.pack(pady=5, padx=10)
        
        sbv_button = tk.Button(
            button_frame,
            text="SBV 변환",
            command=self.convert_sbv,
            font=("맑은 고딕", 10, "bold"),
            bg="#2196F3",
            fg="white",
            width=15,
            height=2
        )
        sbv_button.pack(pady=5, padx=10)
        
        both_button = tk.Button(
            button_frame,
            text="Both\n(SRT + SBV)",
            command=self.convert_both,
            font=("맑은 고딕", 10, "bold"),
            bg="#FF9800",
            fg="white",
            width=15,
            height=2
        )
        both_button.pack(pady=5, padx=10)
        
        # Separator
        separator = tk.Frame(button_frame, height=2, bg="gray")
        separator.pack(fill=tk.X, pady=15, padx=10)
        
        # Download section label
        download_label = tk.Label(
            button_frame,
            text="💾 다운로드",
            font=("맑은 고딕", 11, "bold")
        )
        download_label.pack(pady=(5, 10))
        
        # Download SRT button
        download_srt_button = tk.Button(
            button_frame,
            text="📥 SRT 저장",
            command=self.download_srt,
            font=("맑은 고딕", 9),
            bg="#4CAF50",
            fg="white",
            width=15,
            height=1
        )
        download_srt_button.pack(pady=3, padx=10)
        
        # Download SBV button
        download_sbv_button = tk.Button(
            button_frame,
            text="� SBV 저장",
            command=self.download_sbv,
            font=("맑은 고딕", 9),
            bg="#2196F3",
            fg="white",
            width=15,
            height=1
        )
        download_sbv_button.pack(pady=3, padx=10)
        
        # Separator
        separator2 = tk.Frame(button_frame, height=2, bg="gray")
        separator2.pack(fill=tk.X, pady=15, padx=10)
        
        clear_button = tk.Button(
            button_frame,
            text="�🗑️ 초기화",
            command=self.clear_all,
            font=("맑은 고딕", 10),
            bg="#f44336",
            fg="white",
            width=15,
            height=2
        )
        clear_button.pack(pady=5, padx=10)
        
        # Footer
        footer_label = tk.Label(
            root,
            text="※ 유튜브 Raw Data 매핑 사용 - 1프레임 밀림 방지",
            font=("맑은 고딕", 8),
            fg="blue"
        )
        footer_label.pack(pady=5)
    
    def load_file(self):
        """Load TXT file into input area"""
        file_path = filedialog.askopenfilename(
            title="TXT 파일 선택",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", content)
                    messagebox.showinfo("완료", f"파일 로드 완료!\n{file_path}")
            except Exception as e:
                messagebox.showerror("오류", f"파일 읽기 실패:\n{str(e)}")
    
    def convert_srt(self):
        """Convert to SRT format"""
        try:
            input_data = self.input_text.get("1.0", tk.END)
            subtitles = parse_input_text(input_data)
            
            if not subtitles:
                messagebox.showwarning("경고", "유효한 자막 데이터가 없습니다.\n형식을 확인해주세요.")
                return
            
            result = convert_to_srt(subtitles)
            self.last_srt_result = result  # Store for download
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", result)
            messagebox.showinfo("완료", f"SRT 변환 완료! ({len(subtitles)}개 자막)")
            
        except Exception as e:
            messagebox.showerror("오류", f"변환 중 오류 발생:\n{str(e)}")
    
    def convert_sbv(self):
        """Convert to SBV format"""
        try:
            input_data = self.input_text.get("1.0", tk.END)
            subtitles = parse_input_text(input_data)
            
            if not subtitles:
                messagebox.showwarning("경고", "유효한 자막 데이터가 없습니다.\n형식을 확인해주세요.")
                return
            
            result = convert_to_sbv(subtitles)
            self.last_sbv_result = result  # Store for download
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", result)
            messagebox.showinfo("완료", f"SBV 변환 완료! ({len(subtitles)}개 자막)")
            
        except Exception as e:
            messagebox.showerror("오류", f"변환 중 오류 발생:\n{str(e)}")
    
    def convert_both(self):
        """Convert to both SRT and SBV formats"""
        try:
            input_data = self.input_text.get("1.0", tk.END)
            subtitles = parse_input_text(input_data)
            
            if not subtitles:
                messagebox.showwarning("경고", "유효한 자막 데이터가 없습니다.\n형식을 확인해주세요.")
                return
            
            srt_result = convert_to_srt(subtitles)
            sbv_result = convert_to_sbv(subtitles)
            
            # Store both for download
            self.last_srt_result = srt_result
            self.last_sbv_result = sbv_result
            
            combined = f"========== SRT 형식 ==========\n\n{srt_result}\n\n"
            combined += f"========== SBV 형식 ==========\n\n{sbv_result}"
            
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", combined)
            messagebox.showinfo("완료", f"SRT + SBV 변환 완료! ({len(subtitles)}개 자막)")
            
        except Exception as e:
            messagebox.showerror("오류", f"변환 중 오류 발생:\n{str(e)}")
    
    def download_srt(self):
        """Download SRT file"""
        if not self.last_srt_result:
            messagebox.showwarning("경고", "먼저 SRT 변환을 실행해주세요.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="SRT 파일 저장",
            defaultextension=".srt",
            filetypes=[("SRT Files", "*.srt"), ("All Files", "*.*")],
            initialfile="subtitle.srt"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.last_srt_result)
                messagebox.showinfo("완료", f"SRT 파일 저장 완료!\n{file_path}")
            except Exception as e:
                messagebox.showerror("오류", f"파일 저장 실패:\n{str(e)}")
    
    def download_sbv(self):
        """Download SBV file"""
        if not self.last_sbv_result:
            messagebox.showwarning("경고", "먼저 SBV 변환을 실행해주세요.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="SBV 파일 저장",
            defaultextension=".sbv",
            filetypes=[("SBV Files", "*.sbv"), ("All Files", "*.*")],
            initialfile="subtitle.sbv"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.last_sbv_result)
                messagebox.showinfo("완료", f"SBV 파일 저장 완료!\n{file_path}")
            except Exception as e:
                messagebox.showerror("오류", f"파일 저장 실패:\n{str(e)}")
    
    def clear_all(self):
        """Clear all text fields"""
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self.last_srt_result = ""
        self.last_sbv_result = ""


def main():
    root = tk.Tk()
    app = SubtitleConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
