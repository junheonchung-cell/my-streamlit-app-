import streamlit as st
import requests
from collections import defaultdict

st.set_page_config(page_title="나와 어울리는 영화는?", page_icon="🎬", layout="wide")

# -----------------------------
# TMDB 설정
# -----------------------------
POSTER_BASE = "https://image.tmdb.org/t/p/w500"

GENRES = {
    "액션": 28,
    "코미디": 35,
    "드라마": 18,
    "SF": 878,
    "로맨스": 10749,
    "판타지": 14,
}

GENRE_KR_LABEL = {
    "액션": "액션/어드벤처",
    "코미디": "코미디",
    "드라마": "로맨스/드라마",
    "로맨스": "로맨스/드라마",
    "SF": "SF",
    "판타지": "판타지",
}

# -----------------------------
# 질문/선택지
# -----------------------------
questions = [
    ("1. 주말에 가장 하고 싶은 것은?", ["집에서 휴식", "친구와 놀기", "새로운 곳 탐험", "혼자 취미생활"]),
    ("2. 스트레스 받으면?", ["혼자 있기", "수다 떨기", "운동하기", "맛있는 거 먹기"]),
    ("3. 영화에서 중요한 것은?", ["감동 스토리", "시각적 영상미", "깊은 메시지", "웃는 재미"]),
    ("4. 여행 스타일?", ["계획적", "즉흥적", "액티비티", "힐링"]),
    ("5. 친구 사이에서 나는?", ["듣는 역할", "주도하기", "분위기 메이커", "필요할 때 나타남"]),
]

# 선택지 → 장르 점수 매핑
choice_to_genres = {
    # Q1
    "집에서 휴식": ["드라마", "로맨스"],
    "친구와 놀기": ["코미디"],
    "새로운 곳 탐험": ["액션", "판타지"],
    "혼자 취미생활": ["SF", "판타지"],

    # Q2
    "혼자 있기": ["드라마"],
    "수다 떨기": ["코미디", "로맨스"],
    "운동하기": ["액션"],
    "맛있는 거 먹기": ["코미디"],

    # Q3
    "감동 스토리": ["드라마", "로맨스"],
    "시각적 영상미": ["액션", "판타지"],
    "깊은 메시지": ["SF"],
    "웃는 재미": ["코미디"],

    # Q4
    "계획적": ["SF"],
    "즉흥적": ["로맨스", "코미디"],
    "액티비티": ["액션"],
    "힐링": ["드라마", "로맨스"],

    # Q5
    "듣는 역할": ["드라마"],
    "주도하기": ["액션"],
    "분위기 메이커": ["코미디"],
    "필요할 때 나타남": ["SF", "판타지"],
}

# -----------------------------
# TMDB 호출 함수
# -----------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_popular_movies_by_genre(api_key: str, genre_id: int, limit: int = 6):
    """
    3열 카드로 보여주기 위해 기본 6개(= 2줄) 가져오도록 설정
    """
    url = "https://api.themoviedb.org/3/discover/movie"
    params = {
        "api_key": api_key,
        "with_genres": genre_id,
        "language": "ko-KR",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "page": 1,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])[:limit]
    return results

def analyze_answers(answers: dict):
    scores = defaultdict(int)
    matched = defaultdict(list)

    for _, a in answers.items():
        if not a:
            continue
        for g in choice_to_genres.get(a, []):
            scores[g] += 1
            matched[g].append(a)

    if not scores:
        return None, {}, {}

    # 동점 시 우선순위
    tie_priority = ["드라마", "로맨스", "코미디", "액션", "SF", "판타지"]

    top_score = max(scores.values())
    top_genres = [g for g, s in scores.items() if s == top_score]
    top_genres.sort(key=lambda g: tie_priority.index(g) if g in tie_priority else 999)

    chosen_genre = top_genres[0]
    return chosen_genre, dict(scores), dict(matched)

def make_reason(chosen_genre: str, matched: dict):
    picks = matched.get(chosen_genre, [])
    uniq = []
    for x in picks:
        if x not in uniq:
            uniq.append(x)
    uniq = uniq[:2]

    if uniq:
        return f"당신의 답변(예: {', '.join(uniq)})에서 **{GENRE_KR_LABEL.get(chosen_genre, chosen_genre)}** 성향이 강하게 나타났어요!"
    return f"당신의 응답 패턴을 종합해 **{GENRE_KR_LABEL.get(chosen_genre, chosen_genre)}** 장르가 가장 잘 어울려요!"

# -----------------------------
# UI
# -----------------------------
st.title("🎬 나와 어울리는 영화는?")
st.write("간단한 질문 5개로 당신의 영화 취향을 분석하고, TMDB에서 인기 영화를 예쁘게 추천해드려요! 🍿")

st.sidebar.header("🔑 TMDB 설정")
api_key = st.sidebar.text_input("TMDB API Key", type="password", help="TMDB에서 발급받은 API Key를 입력하세요.")
st.sidebar.caption("※ 키는 앱 실행 중에만 사용되며 저장하지 않아요(코드 기준).")

st.divider()

answers = {}
all_answered = True

for q, options in questions:
    a = st.radio(q, options, index=None)
    answers[q] = a
    if a is None:
        all_answered = False

st.divider()

if st.button("결과 보기", type="primary"):
    # 검증
    if not api_key:
        st.error("사이드바에 TMDB API Key를 입력해 주세요.")
        st.stop()

    if not all_answered:
        st.warning("모든 질문(5개)에 답하면 결과를 더 정확히 추천할 수 있어요!")
        st.stop()

    # 분석
    chosen_genre, scores, matched = analyze_answers(answers)
    if not chosen_genre:
        st.error("답변을 분석할 수 없어요. 다시 시도해 주세요.")
        st.stop()

    genre_label = GENRE_KR_LABEL.get(chosen_genre, chosen_genre)

    # 요구사항 1) 결과 제목
    st.markdown(f"## 🎉 당신에게 딱인 장르는: **{genre_label}**!")
    st.caption(make_reason(chosen_genre, matched))

    # TMDB 로딩
    genre_id = GENRES[chosen_genre]
    with st.spinner("분석 중... (TMDB에서 영화 불러오는 중)"):
        try:
            movies = fetch_popular_movies_by_genre(api_key, genre_id, limit=6)
        except requests.HTTPError as e:
            st.error(f"TMDB 요청에 실패했어요: {e}")
            st.stop()
        except requests.RequestException as e:
            st.error(f"네트워크 오류가 발생했어요: {e}")
            st.stop()

    if not movies:
        st.warning("해당 장르에서 영화를 찾지 못했어요. 잠시 후 다시 시도해 주세요.")
        st.stop()

    st.divider()
    st.subheader("🍿 추천 영화")

    # 요구사항 2) 영화 카드 3열
    cols = st.columns(3)

    for idx, m in enumerate(movies):
        col = cols[idx % 3]

        title = m.get("title") or m.get("name") or "제목 없음"
        rating = m.get("vote_average", 0.0)
        overview = m.get("overview") or "줄거리 정보가 없어요."
        poster_path = m.get("poster_path")

        with col:
            # 간단 카드 스타일
            with st.container(border=True):
                # 요구사항 3) 포스터/제목/평점
                if poster_path:
                    st.image(POSTER_BASE + poster_path, use_container_width=True)
                else:
                    st.write("🖼️ 포스터 없음")

                st.markdown(f"**{title}**")
                st.write(f"⭐ 평점: **{rating:.1f}**")

                # 요구사항 4) 클릭하면 상세 (expander)
                with st.expander("상세 정보 보기"):
                    st.write(overview)
                    st.markdown(
                        f"**이 영화를 추천하는 이유**: {make_reason(chosen_genre, matched)}"
                    )




