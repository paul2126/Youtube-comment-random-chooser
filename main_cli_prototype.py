import os
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json

# load setting from settings.json
try:
    with open("settings.json", "r", encoding="utf-8") as file:
        settings = json.load(file)
except UnicodeDecodeError:
    with open("settings.json", "r", encoding="cp949") as file:
        settings = json.load(file)

html_name = settings["html_name"]
email_types = settings["email_types"]
pick_number = settings["pick_number"]
show_process = settings["show_process"]


def get_comments():
    # Try to load the HTML content from the file with UTF-8 encoding
    try:
        with open(html_name, "r", encoding="utf-8") as file:
            html_content = file.read()
    except UnicodeDecodeError:
        # If UTF-8 fails, try with CP949 encoding
        with open(html_name, "r", encoding="cp949") as file:
            html_content = file.read()

    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")

    # Find all comment elements
    comment_elements = soup.find_all("yt-attributed-string", id="content-text")
    time_elements = soup.find_all("span", id="published-time-text")

    # 댓글 내용
    comments = [
        re.sub(r"\s+", " ", comment.get_text(strip=True))
        for comment in comment_elements
    ]
    # 댓글 시간
    times = [time.get_text(strip=True) for time in time_elements]
    # 이메일 타입
    emails = []
    for comment in comments:
        found = False
        for email_type in email_types:
            if email_type in comment:
                emails.append(email_type)
                found = True
                break
        if not found:  # 이메일 타입이 없는 경우
            emails.append("기타")

    result = []

    for i in range(len(comments)):
        result.append([times[i], comments[i], emails[i]])

    # 계산과정 출력
    if show_process:
        print("전체 이메일 내용: ")
        for i in range(len(comments)):
            print(f"{times[i]}: {comments[i]} ({emails[i]})")

    print(f"총 댓글 수: {len(comments)}개")
    print()

    return result


def save_comments(comments, filename):
    """
    comments: get_comments에서 반환된 댓글 리스트입니다. [[time, comment, email_type], ...] 형태
    주어진 comments를 파일 (yyyy-mm-dd_{filename}.txt) 로 저장합니다.
    여러번 실행되면 덮어씌웁니다.
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    directory = "history"

    # Create directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    with open(
        f"./history/{current_date}_{filename}.txt", "w", encoding="utf-8"
    ) as file:
        for comment in comments:
            file.write(", ".join(comment) + "\n")


def overdue_comments(comments, end_date):
    """
    comments: get_comments에서 반환된 댓글 리스트입니다. [[time, comment, email_type], ...] 형태
    종료 일자 이후 댓글이 있는지 확인하고 있다면 출력해줍니다.
    """
    threshold = __time_conversion(end_date)  # 종료일자로부터 며칠이 지났는지
    cnt_overdue = 0
    cnt_not_overdue = 0
    result = []
    for comment in comments:
        if int(re.match(r"\d+", comment[0]).group()) >= threshold - 1:
            # within due date
            if show_process:
                print(f"종료일자 이전 댓글: {comment[0]}, {comment[1]}")
            result.append(comment)
            cnt_not_overdue += 1
        else:
            # overdue
            if show_process:
                print(f"종료일자 이후 댓글: {comment[0]}, {comment[1]}")
            cnt_overdue += 1

    print(f"종료일자 이후 댓글: {cnt_overdue}개")
    print(f"종료일자 이전 댓글: {cnt_not_overdue}개")
    print()

    return result


def find_email(comments):
    """
    comments: get_comments에서 반환된 댓글 리스트입니다. [[time, comment, email_type], ...] 형태
    댓글 중 이메일 주소를 찾아 출력해줍니다.
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
                if show_process:
                    print(f"이메일: {email}")
                break
            else:
                # 댓글에 숫자가 들어간 경우
                cnt_not_email += 1
                if show_process:
                    print(f"이메일이 아닌 것: {email}")

    print(f"이메일: {cnt_email}개")
    print(f"이메일이 아닌 것: {cnt_not_email}개")
    print()

    return result


def find_duplicate_comments(emails):
    """
    emails: find_email에서 반환된 댓글 리스트입니다. [[email, email_type], ...] 형태
    중복된 이메일이 있다면 찾아서 출력해줍니다.
    """
    email_list = [email[0] for email in emails]
    duplicate_emails = set(
        [email for email in email_list if email_list.count(email) > 1]
    )
    filtered_emails = [email for email in emails if email[0] not in duplicate_emails]
    if duplicate_emails:
        print(f"중복된 이메일: {duplicate_emails}")
    else:
        print("중복된 이메일이 없습니다.")

    return filtered_emails


def random_picker(emails, num):
    """
    emails: find_email에서 반환된 댓글 리스트입니다. [[email, email_type], ...] 형태
    num: 랜덤으로 뽑을 댓글의 개수입니다.
    랜덤으로 댓글을 뽑아 출력해줍니다.
    """
    import random

    random_emails = random.sample(emails, num)
    for email in random_emails:
        print(f"{email[0]}@{email[1]}")

    print("마스킹된 이메일 주소:")
    # 마스킹된 이메일 주소 출력
    for email in random_emails:
        print(f"{email[0][:-4]}****@{email[1]}")
    print()


def __time_conversion(end_date):
    """
    end_date: 종료일자를 받아옵니다. ex) 01/01
    종료일자 부터 현재 날짜 거리를 계산하여 출력해줍니다.
    """
    current_year = datetime.now().year
    end_date_with_year = f"{current_year}/{end_date}"
    date_diff = datetime.now() - datetime.strptime(end_date_with_year, "%Y/%m/%d")
    print(f"종료일({end_date})으로부터 {date_diff.days}일 지났습니다.")
    print()

    return date_diff.days


if __name__ == "__main__":
    due_date = input("종료일자를 넣어주세요(mm/dd) ex) 01/01: ")
    # output error if end_date is not in the correct format
    if not re.match(r"\d{2}/\d{2}", due_date):
        raise ValueError("종료일자는 mm/dd 형식으로 입력해주세요.")
    comments = get_comments()
    save_comments(comments, "필터링전")
    comments_remove_overdue = overdue_comments(comments, due_date)
    comments_emails = find_email(comments_remove_overdue)
    comments_remove_duplicate = find_duplicate_comments(comments_emails)
    save_comments = save_comments(comments_remove_duplicate, "필터링후")
    random_picker(comments_remove_duplicate, pick_number)
