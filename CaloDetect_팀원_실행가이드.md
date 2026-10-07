# 팀원 안내 — VS Code에서 develop 업데이트

이미 한 번 설치하고 실행한 팀원용입니다. **기존에 클론한 폴더에서 업데이트하세요.**

1. 실행 중인 Backend·Frontend 터미널에서 **Ctrl+C**를 누릅니다.
2. VS Code에서 **파일 → 폴더 열기**로 기존 **CaloDetect 폴더**를 엽니다.
3. **왼쪽 아래 브랜치 이름**을 클릭하고 **develop**을 선택합니다. 이미 develop이면 그대로 둡니다.
4. **Ctrl+Shift+P** → **Git: Pull from...** 입력·선택 → **origin** → **develop**을 선택합니다.
5. 완료되면 GitHub의 변경사항이 기존 파일에 반영됩니다. **평소 실행하던 방법으로 Backend·Frontend를 다시 켭니다.**

**새로 클론하거나 ZIP을 받을 필요가 없습니다. 기존 `.env`와 DB는 그대로 사용합니다.**

버튼을 찾기 어려우면 VS Code의 **터미널 → 새 터미널**에서 아래 두 줄을 실행해도 같습니다. 기존 CaloDetect 폴더 안에서 실행하세요.

```powershell
git switch develop
git pull --ff-only origin develop
```

- `Already up to date`가 나오면 이미 최신입니다.
- 직접 수정한 파일 때문에 오류가 나면 **수정 내용을 지우지 말고 팀 리드에게 오류를 보내세요.**
- 실행 중 패키지·설정 오류가 나오면 [README 실행 안내](README.md#새-웹-환경-실행--팀원용-간편-설치)를 확인하세요.

[GitHub develop 보기](https://github.com/wndnsud-ui/CaloDetect/tree/develop) · [VS Code 공식 Pull 안내](https://code.visualstudio.com/docs/sourcecontrol/repos-remotes)
