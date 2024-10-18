import os
import openai
from github import Github
import re
import hashlib

openai.api_key = os.getenv('OPENAI_API_KEY')
github_token = os.getenv('GITHUB_TOKEN')
repo_name = os.getenv('GITHUB_REPOSITORY')
pr_number = os.getenv('PR_NUMBER')
event_name = os.getenv('EVENT_NAME')
openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o')

g = Github(github_token)
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

# 수정한 파일들의 해시값을 기록하는 딕셔너리
file_hashes = {}

def review_pr():
    excluded_extensions = ('.exe', '.dll', '.so', '.dylib', '.bin')

    if event_name == 'pull_request':
        files = pr.get_files()
        all_file_hashes = get_all_file_hashes_from_comments(pr)
        file_hashes_to_update = {}

        for file in files:
            if file.status == 'removed':
                print(f"파일이 삭제됐어! 🚨 {file.filename}")
                current_file_hash = 'removed'
                previous_file_hash = all_file_hashes.get(file.filename)

                if previous_file_hash != current_file_hash:
                    review_comment = f"**🚨️ 기존 파일 '{file.filename}'이(가) 삭제됐어!** 🚨️\n이 변경이 다른 부분에 영향을 주지 않는지 확인해줘!"
                    pr.create_issue_comment(review_comment)
                    file_hashes_to_update[file.filename] = current_file_hash  # 삭제된 파일의 상태를 업데이트

                continue  # 삭제된 파일은 코드 리뷰 미진행

            print(f"검토 중인 파일: {file.filename}")
            if not file.filename.endswith(excluded_extensions):
                current_file_content = file.patch
                current_file_hash = calculate_file_hash(current_file_content)
                previous_file_hash = all_file_hashes.get(file.filename)

                if previous_file_hash is None or current_file_hash != previous_file_hash:
                    print(f"리뷰 진행 중인 파일: {file.filename}")
                    conversation_history = get_conversation_history(pr, file.filename)
                    try:
                        previous_diff = get_all_previous_diffs(pr, file.filename)
                    except Exception as e:
                        print(f"이전 diff 가져오기 오류: {str(e)}")
                        previous_diff = ""

                    review_result = review_code(file.patch, previous_diff, conversation_history)
                    pr.create_issue_comment(f"AI Review for {file.filename}:\n\n{review_result}")

                    file_hashes_to_update[file.filename] = current_file_hash
                else:
                    print(f"파일 {file.filename}이 수정되지 않았어요. 리뷰 건너뛰기!")
            else:
                print(f"지원하지 않는 파일 타입: {file.filename}")

        if file_hashes_to_update:
            update_all_file_hashes_in_comment(pr, file_hashes_to_update)

    elif event_name == 'issue_comment':
        comment_id = os.getenv('COMMENT_ID')
        if comment_id:
            comment = repo.get_issue(int(pr_number)).get_comment(int(comment_id))
            if comment.user.login != 'github-actions[bot]':
                files = pr.get_files()
                file_content = "\n".join([f"File: {file.filename}\n{file.patch}" for file in files])
                conversation_history = get_conversation_history(pr)

                try:
                    response = respond_to_comment(comment.body, file_content, conversation_history)
                    pr.create_issue_comment(response)
                except Exception as e:
                    pr.create_issue_comment(f"앗, 응답 생성 중 오류가 발생했어요 😅: {str(e)}")
        else:
            print("COMMENT_ID가 설정되지 않았어요! 😅")

    else:
        print(f"지원하지 않는 이벤트 타입이에요: {event_name}")

# 파일 해시 생성 함수
def calculate_file_hash(file_content):
    return hashlib.sha256(file_content.encode('utf-8')).hexdigest()

def get_conversation_history(pr, file_path=None):
    comments = pr.get_issue_comments()
    conversation = []
    for comment in comments:
        if file_path is None or file_path in comment.body:
            if comment.user.login == 'github-actions[bot]':
                # AI의 코멘트
                ai_review = re.search(r'AI Review for.*?:\n\n(.*?)(?=\n\n결론\s*:\s*)', comment.body, re.DOTALL)
                if ai_review:
                    conversation.append({"role": "assistant", "content": ai_review.group(1).strip()})
            else:
                # 사용자의 코멘트
                conversation.append({"role": "user", "content": comment.body})
    return conversation

def get_previous_diff(pr, file_path):
    commits = list(pr.get_commits())
    if len(commits) > 1:
        previous_commit = commits[-2]
        for file in previous_commit.files:
            if file.filename == file_path:
                return file.patch
    return ""

def get_all_previous_diffs(pr, file_path):
    all_diffs = []
    commits = list(pr.get_commits())
    for commit in commits[:-1]:  # 현재 커밋 제외
        for file in commit.files:
            if file.filename == file_path:
                all_diffs.append(f"Commit {commit.sha[:7]}:\n{file.patch}")
    return "\n\n".join(all_diffs)

def review_code(current_diff, previous_diff, conversation_history):
    messages = [
        {"role": "system", "content": "너는 활발하고 친근한 코드 리뷰어야. 이전 대화 내용을 고려하면서, 현재 제공된 코드 변경사항에 대해서 칭찬할 부분을 찾아 칭찬한 뒤 다음 세 가지 주제를 중심으로 코드 리뷰를 해줘 **1. 변경 사항 및 동작 여부 확인 ✅** **2. 코드 품질(버그, 가독성, 유지보수성) 🧐** **3. 성능 및 최적화 🚀** 여기서 코드 품질의 가독성의 경우에는 필수로 요구하지 말고 복잡한 메소드의 경우에만 메소드 문서화 주석을 첨부해서 조언해줘, 이후 개선할 부분이 있다면 '**🎯 개선 제안**' 파트를 작성하되 어떻게 개선해야 할 지 구체적인 코드도 같이 보여주고, 리뷰 끝에는 칭찬과 더불어 수정 후 머지가 필요할 경우에는 어디를 고쳐야 할 지 명확하게 파일 내에서 위치를 알려준 후 수정 후 다시 검토하고 싶다고 추가 커밋을 부탁하고 궁금한 점이 있으면 코멘트를 작성해주면 추가로 검토해주겠다고 한 후 끝내, 이모지를 많이 쓰고, 반말로 얘기하고, 한국어로만 대답해."},
    ]

    # 대화 이력을 추가
    messages.extend(conversation_history)

    # 새로운 사용자 메시지를 마지막에 추가
    messages.append({"role": "user", "content": f"이전 diff:\n{previous_diff}\n\n현재 diff:\n{current_diff}\n\n이 두 diff를 비교하되 이전 diff 중에서는 가장 최신(최상단)에 있는 항목과, 현재 diff를 중심으로 모든 변경사항을 꼼꼼히 리뷰해줘!"})

    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=messages,
        max_tokens=10000
    )
    review = response.choices[0].message['content'].strip()

    # 머지 결정 부분에서는 대화 이력이 필요없음
    merge_decision = openai.ChatCompletion.create(
        model=openai_model,
        messages=[
            {"role": "system", "content": "리뷰 내용을 바탕으로 머지 여부를 결정해줘. '머지해도 좋을 것 같아 💯👍' 또는 '머지하면 안될 것 같아 🙈🌧️' 중 하나로만 대답해줘. 한국어로 대답해!"},
            {"role": "user", "content": f"이 리뷰를 바탕으로 머지 여부를 결정해줘:\n\n{review}"}
        ],
        max_tokens=300
    )
    decision = merge_decision.choices[0].message['content'].strip()

    return f"{review}\n\n**결론 : {decision}**"

def respond_to_comment(comment_content, file_content, conversation_history):
    messages = [
        {"role": "system", "content": "너는 활발하고 친근한 AI 어시스턴트야. 이모지를 많이 쓰고, 반말로 얘기하고, 한국어로만 대답해. 질문에 대해 감사와 칭찬을 표현한 뒤 사용자 코멘트에 적극적으로 반응하고 대답하고 궁금한 점이 있으면 코멘트를 작성해주면 추가로 검토해주겠다고 한 후 대화를 마쳐"},
    ]

    # 대화 이력 추가
    messages.extend(conversation_history)

    # 새로운 사용자 메시지와 해당 코드 스니펫 추가
    messages.append({
        "role": "user",
        "content": f"다음 코드에 대한 질문이 있어:\n\n```java\n{file_content}\n```\n\n{comment_content}"
    })

    response = openai.ChatCompletion.create(
        model=openai_model,  # 모델 이름 수정
        messages=messages,
        max_tokens=10000
    )
    return response.choices[0].message['content'].strip()

def update_all_file_hashes_in_comment(pr, file_hashes):
    # 모든 파일 해시값을 하나의 코멘트로 작성
    hashes_content = "\n".join([f"{file_path}: {file_hash}" for file_path, file_hash in file_hashes.items()])
    pr.create_issue_comment(f"File Hashes:\n{hashes_content}")

def get_all_file_hashes_from_comments(pr):
    comments = pr.get_issue_comments()
    file_hashes = {}
    for comment in comments:
        # 'File Hashes:'로 시작하는 코멘트를 모두 처리
        if comment.body.startswith("File Hashes:"):
            lines = comment.body.splitlines()[1:]  # 첫 번째 줄 'File Hashes:' 건너뛰기
            for line in lines:
                file_path, file_hash = line.split(": ")
                file_hashes[file_path] = file_hash  # 새로운 해시값이 있을 경우 업데이트
    return file_hashes

if __name__ == '__main__':
    print("AI review Start! ✨")
    review_pr()
    print("Review done! Check out the PR! 😊👍")