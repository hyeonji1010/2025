pip install git+https://github.com/ssut/py-hanspell.git
from hanspell import spell_checker

def rude_spell_checker(text):
    result = spell_checker.check(text)
    checked_text = result.checked
    errors = result.errors

    if errors:
        print("문장 꼬라지 봐라. 발로 썼냐?")
        print(f"> 머저리 같은 네 문장: {text}")
        print(f"> 자애로운 내가 고친 문장: {checked_text}")
        print("축하해, 넌 내가 아는 생물 중 단연코 가장 멍청한 자식이야.")
    else:
        print("허. 그래, 이건 맞네. 드물게 잘했어.")

if __name__ == "__main__":
    while True:
        user_input = input("뭐라고 쓸 건데? (꺼질거면 'exit' 입력.): ")
        if user_input.lower() == 'exit':
            print("드디어! 난 간다 빌어먹을 유기물아.")
            break
        rude_spell_checker(user_input)
