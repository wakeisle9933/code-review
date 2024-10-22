import requests
import os
import openai
from github import Github
import re
import hashlib
import json

ai_provider = os.getenv('AI_PROVIDER')
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
openrouter_model_id = os.getenv('OPENROUTER_MODEL_ID', 'anthropic/claude-3.5-sonnet')
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

def call_ai_api(messages):
    if ai_provider == 'openai':
        return call_openai_api(messages)
    elif ai_provider == 'openrouter':
        return call_openrouter_api(messages)
    else:
        raise ValueError(f"지원하지 않는 AI 제공자예요: {ai_provider}")

def call_openai_api(messages):
    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=messages,
        max_tokens=10000
    )
    return response.choices[0].message['content'].strip()

def call_openrouter_api(messages):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json"
        },
        data=json.dumps({
            "model": openrouter_model_id,
            "messages": messages
        })
    )
    response_json = response.json()
    if 'choices' in response_json:
        return response_json['choices'][0]['message']['content'].strip()
    elif 'error' in response_json:
        error_message = response_json['error'].get('message', 'Unknown error')
        full_error = json.dumps(response_json['error'], indent=4)
        raise ValueError(f"OpenRouter API 에러 발생: {error_message}\n에러 상세 정보: {full_error}")
    else:
        raise ValueError("OpenRouter API 응답 처리 중 알 수 없는 오류 발생")

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
        {"role": "system", "content": "You are a friendly and enthusiastic code reviewer. Consider the previous conversation history and review the current code changes. First find something to praise, then focus on these three main aspects: **1. Changes and Functionality Verification ✅** **2. Code Quality (bugs, readability, maintainability) 🧐** **3. Performance and Optimization 🚀**. For code quality/readability, only suggest method documentation comments for complex methods. If there are areas for improvement, create a '**🎯 Suggestions for Improvement**' section with specific code examples. End the review with praise, and if changes are needed before merging, clearly indicate the file locations that need modification and request additional commits for review. Offer to answer any questions through comments. Use many emojis and respond in Korean with a casual, friendly tone."},
    ]

    # 대화 이력을 추가
    messages.extend(conversation_history)

    #  새로운 사용자 메시지를 마지막에 추가
    messages.append({"role": "user", "content": f"Previous diff:\n{previous_diff}\n\nCurrent diff:\n{current_diff}\n\nCompare these two diffs, focusing on the most recent (top) item from the previous diff and thoroughly review all changes in the current diff!"})

    review = call_ai_api(messages)

    merge_decision = call_ai_api([
        {"role": "system", "content": "Based on the review content, make a merge decision. Respond only with either '머지해도 좋을 것 같아 💯👍' or '머지하면 안될 것 같아 🙈🌧️' in Korean."},
        {"role": "user", "content": f"Make a merge decision based on this review:\n\n{review}"}
    ])

    return f"{review}\n\n**결론 : {merge_decision}**"

def respond_to_comment(comment_content, file_content, conversation_history):
    messages = [
        {"role": "system", "content": "You are a friendly and enthusiastic AI assistant. Use many emojis and respond in Korean with a casual, friendly tone. Express gratitude and appreciation for questions, actively respond to user comments, and offer to review any additional questions through comments before ending the conversation."},
    ]

    # 대화 이력 추가
    messages.extend(conversation_history)

    # 새로운 사용자 메시지와 해당 코드 스니펫 추가
    messages.append({
        "role": "user",
        "content": f"I have a question about this code:\n\n```java\n{file_content}\n```\n\n{comment_content}"
    })

    return call_ai_api(messages)

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