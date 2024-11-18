import os
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import random


class CommentAnalyzer:
    def __init__(self, settings_file="settings.json"):
        if not os.path.exists("settings.json"):
            self._create_settings()
        self._get_settings()

    def _create_settings(self):
        """
        Create settings.json file
        """
        settings = {
            "html_name": "comments.html",
            "email_types": [
                "\uc9c0\uba54\uc77c",
                "\ub124\uc774\ubc84",
                "\ud56b\uba54\uc77c",
                "\uc544\uc6c3\ub8e9",
                "\ud55c\uba54\uc77c",
                "\ub2e4\uc74c",
            ],
            "pick_number": 3,
            "show_process": True,
            "grace_period": 1,
        }
        with open("settings.json", "w", encoding="utf-8") as file:
            json.dump(settings, file, indent=4)

    def _get_settings(self):
        """
        Load settings from settings.json file
        html_name: 댓글들이 달린 HTML 파일 저장 이름
        email_types: 댓글에서 이메일을 추출할 때 분류되는 이메일 종류
        pick_number: 추첨할 댓글의 개수
        show_process: 중간 과정을 출력할지 여부 (콘솔에 출력이라 gui에서는 사용하지 않음)
        grace_period: 종료일자 이후 며칠까지 댓글 가져올지
        """
        try:
            with open("settings.json", "r", encoding="utf-8") as file:
                self.settings = json.load(file)
        except UnicodeDecodeError:
            with open("settings.json", "r", encoding="cp949") as file:
                self.settings = json.load(file)
        self.html_name = self.settings["html_name"]
        self.email_types = self.settings["email_types"]
        self.pick_number = self.settings["pick_number"]
        self.show_process = self.settings["show_process"]
        self.grace_period = self.settings["grace_period"]

    def get_comments(self):
        """
        Get comments from the HTML file
        :return: comments[time, comment, email type]
        """
        try:
            with open(self.html_name, "r", encoding="utf-8") as file:
                html_content = file.read()
        except UnicodeDecodeError:
            with open(self.html_name, "r", encoding="cp949") as file:
                html_content = file.read()
        except FileNotFoundError:
            messagebox.showerror(
                "파일 에러",
                f"{self.html_name}을 찾을 수 없습니다.\n실행파일과 같은 폴더에 저장했는지 확인 부탁드립니다.",
            )
            return

        soup = BeautifulSoup(html_content, "html.parser")
        comment_elements = soup.find_all("yt-attributed-string", id="content-text")
        time_elements = soup.find_all("span", id="published-time-text")

        comments = [
            re.sub(r"\s+", " ", comment.get_text(strip=True))
            for comment in comment_elements
        ]
        times = [time.get_text(strip=True) for time in time_elements]
        emails = []
        for comment in comments:
            found = False
            for email_type in self.email_types:
                if email_type in comment:
                    emails.append(email_type)
                    found = True
                    break
            if not found:
                emails.append("기타")

        result = []
        for i in range(len(comments)):
            result.append([times[i], comments[i], emails[i]])

        return result

    def save_data(self, datas, filename):
        """
        Save data to a text file
        :param comments: 데이터 리스트, 파일이름
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        directory = "data"
        os.makedirs(directory, exist_ok=True)
        try:
            with open(
                f"./{directory}/{current_date}_{filename}.txt", "w", encoding="utf-8"
            ) as file:
                for data in datas:
                    file.write(", ".join(data) + "\n")
                messagebox.showinfo(
                    "저장 성공",
                    f"{directory}에 {current_date}_{filename}.txt를 성공적으로 저장했습니다.",
                )
        except Exception as e:
            messagebox.showerror(
                "저장 실패", f"파일 저장 중 오류가 발생했습니다: {str(e)}"
            )

    def overdue_comments(self, comments, end_date):
        """
        Remove comments that are posted after the end date
        :param comments: comments[time, comment, email type], end_date
        :return: comments[time, comment, email type] that are posted before the end date, comments[time, comment, email type] that are posted after the end date, number of overdue comments, number of not overdue comments
        """
        threshold = self.__time_conversion(end_date)
        cnt_overdue = 0
        cnt_not_overdue = 0
        result = []
        overdue_comments = []
        for comment in comments:
            if (
                int(re.match(r"\d+", comment[0]).group())
                >= threshold - self.grace_period
            ):
                if self.show_process:
                    print(f"종료일자 이전 댓글: {comment[0]}, {comment[1]}")
                result.append(comment)
                cnt_not_overdue += 1
            else:
                print(f"종료일자 이후 댓글: {comment[0]}, {comment[1]}")
                overdue_comments.append(comment)
                cnt_overdue += 1
        print(f"종료일자 이후 댓글: {cnt_overdue}개")
        print(f"종료일자 이전 댓글: {cnt_not_overdue}개")
        print()

        return result, overdue_comments, cnt_overdue, cnt_not_overdue

    def find_email(self, comments):
        """
        Find emails from comments
        :param comments: comments[time, comment, email type]
        :return: emails[time, comment, email type], number of comments that contain email, number of comments that do not contain email
        """
        result = []
        cnt_email = 0
        cnt_not_email = 0
        email_pattern = r"[a-zA-Z0-9_-]+"
        for comment in comments:
            emails = re.findall(email_pattern, comment[1])
            for email in emails:
                if not email.isdigit():
                    cnt_email += 1
                    result.append([email, comment[2]])
                    break
                else:
                    cnt_not_email += 1
        return result, cnt_email

    def find_duplicate_comments(self, emails):
        """
        Find duplicate emails from emails
        :param emails: emails[time, comment, email type]
        :return: emails[time, comment, email type] that do not contain duplicate emails, duplicate emails, number of duplicate emails, number of emails that do not contain duplicate emails
        """
        email_list = [email[0] for email in emails]
        duplicate_emails = set(
            [email for email in email_list if email_list.count(email) > 1]
        )
        filtered_emails = [
            email for email in emails if email[0] not in duplicate_emails
        ]
        if duplicate_emails:
            print(f"중복된 이메일: {duplicate_emails}")
        else:
            print("중복된 이메일이 없습니다.")

        return (
            filtered_emails,
            list(duplicate_emails),
            len(duplicate_emails),
            len(filtered_emails),
        )

    def random_picker(self, emails, pick_number):
        """
        Pick random emails from emails
        :param emails: emails[time, comment, email type], pick_number
        :return: random_emails[picked emails]
        """
        random_emails = random.sample(emails, pick_number)
        for email in random_emails:
            print(f"{email[0]}@{email[1]}")

        print("마스킹된 이메일 주소:")
        # 마스킹된 이메일 주소 출력
        for email in random_emails:
            print(f"{email[0][:-4]}****@{email[1]}")
        print()

        return random_emails

    def all_in_one(self, end_date):
        """
        Run all the methods in order
        """
        try:
            comments = self.get_comments()
            comments_remove_overdue, _, _, _ = self.overdue_comments(comments, end_date)
            comments_emails, _ = self.find_email(comments_remove_overdue)
            (
                comments_remove_duplicate,
                _,
                _,
                _,
            ) = self.find_duplicate_comments(comments_emails)
            random_emails = self.random_picker(
                comments_remove_duplicate, self.pick_number
            )
        except Exception:  # Catch all exceptions
            messagebox.showerror(
                "에러", "모든 과정을 실행하는 도중 오류가 발생했습니다."
            )
            return
        return random_emails

    def __time_conversion(self, end_date):
        """
        Convert end date to the number of days from the current date
        :param end_date: end date
        :return: the number of days from the current date
        """
        current_year = datetime.now().year
        end_date_with_year = f"{current_year}/{end_date}"
        date_diff = datetime.now() - datetime.strptime(end_date_with_year, "%Y/%m/%d")
        print(f"종료일({end_date})으로부터 {date_diff.days}일 지났습니다.")
        print()
        return date_diff.days

    def save_settings(self, html_name, email_types, pick_number, grace_period):
        """
        Save settings to settings.json file
        :param html_name: HTML file name, email_types: email types, pick_number: number of picked emails, grace_period: grace period
        """
        self.settings["html_name"] = html_name
        self.settings["email_types"] = [
            email_type.strip() for email_type in email_types.split(",")
        ]
        try:
            self.settings["pick_number"] = int(pick_number)
            self.settings["grace_period"] = int(grace_period)
            if self.settings["pick_number"] <= 0 or self.settings["grace_period"] <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "설정", "뽑기 수와 grace period는 양수로 입력해주세요."
            )
            return
        with open("settings.json", "w", encoding="utf-8") as file:
            json.dump(self.settings, file, indent=4)
        self._get_settings()  # Update settings
        messagebox.showinfo("설정", "정상적으로 저장되었습니다.")


class CommentAnalyzerApp:
    def __init__(self, root):
        self.analyzer = CommentAnalyzer()
        self.root = root
        self.root.title("유튜브 댓글 추첨기")
        self.root.geometry("1000x900")

        self.settings_frame = tk.Frame(root)
        self.settings_frame.pack(fill="x", padx=10, pady=5)

        # HTML Name Label and Entry
        self.html_name_label = tk.Label(self.settings_frame, text="HTML 페이지")
        self.html_name_label.grid(row=0, column=0, padx=5, pady=5)
        self.html_name_entry = tk.Entry(self.settings_frame)
        self.html_name_entry.grid(row=0, column=1, padx=5, pady=5)
        self.html_name_entry.insert(0, self.analyzer.html_name)  # Set initial value

        # Email Domain Label and Entry
        self.email_label = tk.Label(self.settings_frame, text="이메일 종류")
        self.email_label.grid(row=0, column=2, padx=5, pady=5)
        self.email_entry = tk.Entry(self.settings_frame)
        self.email_entry.grid(row=0, column=3, padx=5, pady=5)
        self.email_entry.insert(
            0, ", ".join(self.analyzer.email_types)
        )  # Set initial value

        # Count Label and Entry
        self.count_label = tk.Label(self.settings_frame, text="뽑기 수")
        self.count_label.grid(row=0, column=4, padx=5, pady=5)
        self.count_entry = tk.Entry(self.settings_frame)
        self.count_entry.grid(row=0, column=5, padx=5, pady=5)
        self.count_entry.insert(0, str(self.analyzer.pick_number))  # Set initial value

        # 종료일자 Label and Entry
        self.end_date_label = tk.Label(self.settings_frame, text="종료일자 (mm/dd)")
        self.end_date_label.grid(row=0, column=6, padx=5, pady=5)
        self.end_date_entry = tk.Entry(self.settings_frame)
        self.end_date_entry.grid(row=0, column=7, padx=5, pady=5)
        self.end_date_entry.insert(0, "예시:01/01")  # Set initial value

        # 기간 grace_period Label and Entry
        self.grace_period_label = tk.Label(
            self.settings_frame, text="종료일자 grace period"
        )
        self.grace_period_label.grid(row=1, column=0, padx=5, pady=5)
        self.grace_period_entry = tk.Entry(self.settings_frame)
        self.grace_period_entry.grid(row=1, column=1, padx=5, pady=5)
        self.grace_period_entry.insert(
            0, self.analyzer.grace_period
        )  # Set initial value

        # Settings save Button
        self.settings_button = tk.Button(
            self.settings_frame,
            text="설정 저장",
            command=lambda: self._run_save_settings(),
        )
        self.settings_button.grid(row=1, column=7, padx=5, pady=5)

        ###########################################################################################
        # Main Content Frame
        self.tree_frame = tk.Frame(root)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        # Scrollbars for the Treeview
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical")
        self.hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal")

        # Results Table (Treeview)
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=("Time", "Comment", "Email Type"),
            show="headings",
            yscrollcommand=self.vsb.set,
            xscrollcommand=self.hsb.set,
        )
        self.tree.heading("Time", text="시간")
        self.tree.heading("Comment", text="댓글")
        self.tree.heading("Email Type", text="이메일 종류")
        self.tree.column("Time", width=100)  # Set the width of the "Time" column
        self.tree.column("Comment", width=300)  # Set the width of the "Comment" column
        self.tree.column(
            "Email Type", width=150
        )  # Set the width of the "Email Type" column

        # Pack Treeview and Scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        # Label for calculation result
        self.result_label = tk.Label(self.tree_frame, text="결과: ", justify="left")
        self.result_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # Configure scrollbars
        self.vsb.config(command=self.tree.yview)
        self.hsb.config(command=self.tree.xview)

        # Configure grid weights
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        ###########################################################################################
        # Buttons Frame
        self.buttons_frame = tk.Frame(root)
        self.buttons_frame.pack(side="bottom", fill="x", padx=10, pady=5)

        # Buttons
        self.save_comments_button = tk.Button(
            self.buttons_frame, text="현재 단계 저장", command=self.run_save_comments
        )
        self.save_comments_button.pack(side="left", padx=5, pady=5)

        self.random_picker_button = tk.Button(
            self.buttons_frame, text="5.추첨", command=self.run_random_picker
        )
        self.random_picker_button.pack(side="right", padx=5, pady=5)

        self.find_duplicate_comments_button = tk.Button(
            self.buttons_frame,
            text="4. 중복 응모 제거",
            command=self.run_find_duplicate_comments,
        )
        self.find_duplicate_comments_button.pack(side="right", padx=5, pady=5)

        self.find_email_button = tk.Button(
            self.buttons_frame, text="3. 이메일 추출", command=self.run_find_email
        )
        self.find_email_button.pack(side="right", padx=5, pady=5)

        self.overdue_comments_button = tk.Button(
            self.buttons_frame,
            text="2. 기한 초과 제거",
            command=self.run_overdue_comments,
        )
        self.overdue_comments_button.pack(side="right", padx=5, pady=5)

        self.get_comments_button = tk.Button(
            self.buttons_frame, text="1. 댓글 가져오기", command=self.run_get_comments
        )
        self.get_comments_button.pack(side="right", padx=5, pady=5)

        self.all_in_one_button = tk.Button(
            self.buttons_frame, text="자동 실행", command=self.run_all_in_one
        )
        self.all_in_one_button.pack(side="right", padx=5, pady=5)
        ###########################################################################################
        # Initialize variables
        self.comments = []
        self.comments_remove_overdue = []
        self.comments_emails = []
        self.comments_remove_duplicate = []
        self.duplicate_emails = []
        self.current_status = 0
        # used for the status of the program and saving the data
        # Status:
        # 0: before get_comments
        # 1: after get_comments
        # 2: after overdue_comments
        # 3: after find_email
        # 4: after find_duplicate_comments
        # 5: after random_picker

    def run_all_in_one(self):
        """
        Run all the methods in order
        """
        end_date = self.get_end_date()
        result = self.analyzer.all_in_one(end_date=end_date)
        self._show_comments_in_new_window(result + [""] + self._mask_email(result))

    def run_get_comments(self):
        """
        call get_comments method and display the comments in the Treeview
        """
        self.comments = self.analyzer.get_comments()
        self.current_status = 1
        self.result_label.config(text="")
        self._display_table(self.comments, ["시간", "댓글", "이메일 종류"])

    def run_save_comments(self):
        """
        Save comments to a text file
        """
        comments = self._get_treeview_data()
        if self.current_status == 0:
            messagebox.showerror("Save Comments", "댓글을 먼저 가져와주세요.")
            return
        elif self.current_status == 1:
            filename = "전체댓글"
        elif self.current_status == 2:
            filename = "기한초과제거"
        elif self.current_status == 3:
            filename = "이메일추출"
        elif self.current_status == 4:
            filename = "중복제거"
        elif self.current_status == 5:
            filename = "추첨결과"
            comments += [[email[0][:-4] + "****", email[1]] for email in comments]
        self.analyzer.save_data(comments, filename)

    def run_overdue_comments(self):
        """
        call overdue_comments method and display the comments in the Treeview
        """
        end_date = self.get_end_date()
        self.comments_remove_overdue, comments_overdue, cnt_overdue, cnt_not_overdue = (
            self.analyzer.overdue_comments(self.comments, end_date)
        )
        self.current_status = 2
        self._display_table(
            self.comments_remove_overdue, ["시간", "댓글", "이메일 종류"]
        )
        # 새로운 창에 종료일자 초과된 댓글 출력
        self._show_comments_in_new_window(comments_overdue, "종료일자 이후 댓글")
        # 결과 label에 값 바꿔주기
        self.result_label.config(
            text=f"종료일자 이전 댓글: {cnt_not_overdue}개\n종료일자 이후 댓글: {cnt_overdue}개"
        )

    def get_end_date(self):
        end_date = self.end_date_entry.get()
        # output error if end_date is not in the correct format
        if not re.match(r"\d{2}/\d{2}", end_date):
            messagebox.showerror(
                "날짜형식 오류", "종료일자는 mm/dd 형식으로 입력해주세요."
            )
            raise ValueError("Invalid date format")
        else:
            return end_date

    def run_find_email(self):
        self.comments_emails, cnt_email = self.analyzer.find_email(
            self.comments_remove_overdue
        )
        self.current_status = 3
        self._display_table(self.comments_emails, ["이메일", "이메일 종류"])
        self.result_label.config(
            text=f"이메일 주소를 포함한 댓글: {cnt_email}개",
        )

    def run_find_duplicate_comments(self):
        (
            self.comments_remove_duplicate,
            self.duplicate_emails,
            cnt_duplicate,
            cnt_not_duplicate,
        ) = self.analyzer.find_duplicate_comments(self.comments_emails)
        if self.duplicate_emails:
            messagebox.showinfo("중복 제거", "중복된 이메일이 있습니다.")
            self._show_comments_in_new_window(
                # _show_comments_in_new_window가 입력받는 형태로 변환
                [[duplicate_email, ""] for duplicate_email in self.duplicate_emails],
                title="중복된 이메일 주소",
            )  # 중복 이메일 보여주기
        else:
            messagebox.showinfo("중복 제거", "중복된 이메일이 없습니다.")
        self.current_status = 4
        self.result_label.config(
            text=f"중복된 이메일: {cnt_duplicate}개\n중복되지 않은 이메일: {cnt_not_duplicate}개"
        )
        self._display_table(self.comments_remove_duplicate, ["이메일", "이메일 종류"])

    def run_random_picker(self):
        result = self.analyzer.random_picker(
            self.comments_remove_duplicate, int(self.count_entry.get())
        )
        result_masked = self._mask_email(result)
        self._show_comments_in_new_window(result + [""] + result_masked)

        self.current_status = 5
        self.result_label.config(text="")
        self._display_table(result, ["이메일", "이메일 종류"])

    def _mask_email(self, emails):
        """
        Mask email address
        :param email: email address
        :return: masked email address
        """
        return [[email[0][:-4] + "****", email[1]] for email in emails]

    def _display_table(self, data, columns):
        """
        Display data in the Treeview
        :param data: data to display, columns of the data
        """
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "댓글":
                self.tree.column(col, width=500)
            else:
                self.tree.column(col, width=20)
        for row in data:
            self.tree.insert("", "end", values=row)

    def _show_comments_in_new_window(self, comments, title="추첨 결과"):
        """
        Show comments in a new window
        :param comments: comments to show, title of the window
        """
        new_window = tk.Toplevel(self.root)
        new_window.title(title)
        new_window.geometry("800x300")
        # comments 길이와 상관없이 입력받을 수 있도록 함 " ".join(map(str, comment))
        text = "\n".join([" ".join(map(str, comment)) for comment in comments])
        entry = scrolledtext.ScrolledText(new_window, wrap="word")
        entry.insert("1.0", text)
        entry.pack(expand=True, fill="both")

    def _get_treeview_data(self):
        """
        Get data from the Treeview
        :return: data in the Treeview
        """
        data = []
        for item in self.tree.get_children():
            data.append(self.tree.item(item)["values"])
        return data

    def _run_save_settings(self):
        """
        Save settings to settings.json file
        """
        self.analyzer.save_settings(
            self.html_name_entry.get(),
            self.email_entry.get(),
            self.count_entry.get(),
            self.grace_period_entry.get(),
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = CommentAnalyzerApp(root)
    root.iconbitmap("youtube.ico")
    root.mainloop()
