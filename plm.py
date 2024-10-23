import streamlit as st
import hashlib
import base64
import time
import os
from datetime import datetime, timedelta
from io import BytesIO
try:
    from streamlit_option_menu import option_menu
except ImportError:
    st.error("The 'streamlit-option-menu' package is not installed. Please install it using 'pip install streamlit-option-menu'")
    st.stop()
from PIL import Image, ImageDraw, ImageFont
import io

# Função para criar um logo personalizado
def create_logo():
    img = Image.new('RGB', (300, 100), color='white')
    d = ImageDraw.Draw(img)
    try:
        # Tenta usar uma fonte comum do Windows
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        # Se não encontrar, usa a fonte padrão
        font = ImageFont.load_default()
    d.text((10,35), "Justificações Acadêmicas", fill=(0,0,0), font=font)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

# Configuração da página
st.set_page_config(layout="wide", page_title="Justificações Acadêmicas", page_icon="🎓")

# Estilo CSS personalizado
st.markdown("""
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size:20px !important;
    }
    .stButton>button {
        color: #4F8BF9;
        border-radius: 50px;
        height: 3em;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# Configuração inicial
if 'users_db' not in st.session_state:
    st.session_state.users_db = {
        'admin@email.com': {
            'password': hashlib.sha256('admin123'.encode()).hexdigest(),
            'permissions': ['admin'],
            'last_login': None,
            'session_id': None
        },
        'estudante@email.com': {
            'password': hashlib.sha256('senha123'.encode()).hexdigest(),
            'permissions': ['curso1'],
            'progress': {'curso1': 1},
            'last_login': None,
            'session_id': None
        }
    }

if 'courses_db' not in st.session_state:
    st.session_state.courses_db = {
        f'curso{i}': {
            'name': f'Curso {i}',
            'topics': "",
            'lessons': {},
            'quizzes': {},
            'feedback': []
        } for i in range(1, 11)  # Criando 10 cursos
    }

# Funções auxiliares
def check_password(email, password):
    if email in st.session_state.users_db:
        return st.session_state.users_db[email]['password'] == hashlib.sha256(password.encode()).hexdigest()
    return False

def get_user_permissions(email):
    return st.session_state.users_db[email]['permissions']

def login(email, password):
    if check_password(email, password):
        user = st.session_state.users_db[email]
        current_time = datetime.now()
        if user['session_id'] and user['last_login']:
            last_login = datetime.fromisoformat(user['last_login'])
            if current_time - last_login < timedelta(hours=1):  # Sessão expira após 1 hora
                st.error("Esta conta já está em uso em outra sessão.")
                return False
        session_id = hashlib.sha256(f"{email}{time.time()}".encode()).hexdigest()
        user['session_id'] = session_id
        user['last_login'] = current_time.isoformat()
        st.session_state.logged_in = True
        st.session_state.user_email = email
        st.session_state.session_id = session_id
        return True
    return False

def logout():
    if st.session_state.logged_in:
        user = st.session_state.users_db[st.session_state.user_email]
        user['session_id'] = None
        user['last_login'] = None
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.session_state.session_id = None

def save_uploaded_file(uploaded_file, course, lesson_number, file_type):
    if uploaded_file is not None:
        file_details = {"FileName": uploaded_file.name, "FileType": uploaded_file.type}
        
        # Crie um diretório para armazenar os arquivos se ele não existir
        save_dir = f"course_files/{course}/lesson_{lesson_number}"
        os.makedirs(save_dir, exist_ok=True)
        
        # Salve o arquivo no sistema de arquivos
        file_path = os.path.join(save_dir, uploaded_file.name)
        
        # Use BytesIO para lidar com arquivos grandes
        with BytesIO(uploaded_file.read()) as file_buffer, open(file_path, "wb") as out_file:
            while True:
                chunk = file_buffer.read(1024 * 1024)  # Lê 1MB de cada vez
                if not chunk:
                    break
                out_file.write(chunk)
        
        # Atualize o banco de dados do curso com o caminho do arquivo
        if 'lessons' not in st.session_state.courses_db[course]:
            st.session_state.courses_db[course]['lessons'] = {}
        if lesson_number not in st.session_state.courses_db[course]['lessons']:
            st.session_state.courses_db[course]['lessons'][lesson_number] = {}
        st.session_state.courses_db[course]['lessons'][lesson_number][file_type] = {
            'details': file_details,
            'file_path': file_path
        }
        return True
    return False

def get_binary_file_downloader_html(file_path, file_name):
    with open(file_path, 'rb') as file:
        file_content = file.read()
    b64 = base64.b64encode(file_content).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">Baixar PDF</a>'

def save_quiz(course, lesson_number, questions):
    st.session_state.courses_db[course]['quizzes'][lesson_number] = questions

def check_quiz_answers(course, lesson_number, user_answers):
    correct_answers = st.session_state.courses_db[course]['quizzes'][lesson_number]
    return [ua.lower() == ca['answer'].lower() for ua, ca in zip(user_answers, correct_answers)]

# Interface principal
def main():
    col1, col2, col3 = st.columns([1,3,1])
    with col1:
        st.image(create_logo(), width=300)
    with col2:
        st.markdown('<p class="big-font">Sistema de Cursos Online</p>', unsafe_allow_html=True)
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login_interface()
    else:
        logged_in_interface()

def login_interface():
    st.markdown('<p class="medium-font">Login</p>', unsafe_allow_html=True)
    with st.form("login_form"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input('📧 E-mail')
        with col2:
            password = st.text_input('🔒 Senha', type='password')
        submit_button = st.form_submit_button("🚀 Entrar")
        if submit_button:
            if login(email, password):
                st.success("Login bem-sucedido!")
                st.rerun()
            else:
                st.error('E-mail ou senha incorretos')

def logged_in_interface():
    st.sidebar.markdown(f'👤 Bem-vindo, {st.session_state.user_email}!')
    if 'admin' in get_user_permissions(st.session_state.user_email):
        admin_menu()
    else:
        student_menu()
    if st.sidebar.button('🚪 Logout'):
        logout()
        st.rerun()

def admin_menu():
    choice = option_menu(
        menu_title="Menu Administrativo",
        options=["Gerenciar Cursos", "Gerenciar Usuários", "Gerenciar Conteúdo"],
        icons=["book", "people", "file-earmark-text"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
    )
    if choice == "Gerenciar Cursos":
        manage_courses()
    elif choice == "Gerenciar Usuários":
        manage_users()
    elif choice == "Gerenciar Conteúdo":
        manage_content()

def student_menu():
    permissions = get_user_permissions(st.session_state.user_email)
    choice = option_menu(
        menu_title="Menu do Estudante",
        options=["Meus Cursos", "Progresso", "Ajuda"],
        icons=["book", "graph-up", "question-circle"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
    )
    if choice == "Meus Cursos":
        show_student_courses(permissions)
    elif choice == "Progresso":
        show_student_progress(permissions)
    elif choice == "Ajuda":
        show_help()

def manage_courses():
    st.markdown('<p class="medium-font">Gerenciar Cursos</p>', unsafe_allow_html=True)
    course = st.selectbox('🎓 Selecione um curso', list(st.session_state.courses_db.keys()))
    
    # Editar nome do curso
    new_name = st.text_input("📝 Nome do curso", value=st.session_state.courses_db[course]['name'])
    if new_name != st.session_state.courses_db[course]['name']:
        st.session_state.courses_db[course]['name'] = new_name
        st.success(f"Nome do curso atualizado para: {new_name}")
    
    # Editar tópicos do curso
    topics = st.text_area("📚 Tópicos do curso", value=st.session_state.courses_db[course]['topics'])
    if topics != st.session_state.courses_db[course]['topics']:
        st.session_state.courses_db[course]['topics'] = topics
        st.success("Tópicos do curso atualizados!")
    
    # Visualizar feedback dos estudantes
    if st.button("👀 Ver feedback dos estudantes"):
        feedback = st.session_state.courses_db[course]['feedback']
        if feedback:
            for idx, fb in enumerate(feedback, 1):
                st.write(f"Feedback {idx}: {fb}")
        else:
            st.info("Ainda não há feedback para este curso.")

def manage_users():
    st.markdown('<p class="medium-font">Gerenciar Usuários</p>', unsafe_allow_html=True)
    user_email = st.selectbox('👤 Selecione um usuário', [user for user in st.session_state.users_db if user != 'admin@email.com'])
    user_permissions = st.multiselect('🔐 Selecione os cursos que o usuário pode acessar', 
                                      list(st.session_state.courses_db.keys()), 
                                      default=st.session_state.users_db[user_email]['permissions'])
    if st.button('📝 Atualizar Permissões'):
        st.session_state.users_db[user_email]['permissions'] = user_permissions
        st.success(f"Permissões atualizadas para {user_email}")

def manage_content():
    st.markdown('<p class="medium-font">Gerenciar Conteúdo do Curso</p>', unsafe_allow_html=True)
    course = st.selectbox('🎓 Selecione um curso', list(st.session_state.courses_db.keys()))
    lesson_number = st.selectbox('📚 Selecione o número da aula', range(1, 21))
    st.subheader("📹 Upload de Vídeo")
    video_file = st.file_uploader("Escolha um vídeo para a aula", type=['mp4'])
    if video_file is not None:
        if save_uploaded_file(video_file, course, lesson_number, 'video'):
            st.success(f"Vídeo '{video_file.name}' carregado com sucesso para a aula {lesson_number}")
    st.subheader("📄 Upload de PDF")
    pdf_file = st.file_uploader("Escolha um PDF para a aula", type=['pdf'])
    if pdf_file is not None:
        if save_uploaded_file(pdf_file, course, lesson_number, 'pdf'):
            st.success(f"PDF '{pdf_file.name}' carregado com sucesso para a aula {lesson_number}")
    manage_quiz(course, lesson_number)

def manage_quiz(course, lesson_number):
    st.subheader("❓ Gerenciar Quiz")
    if lesson_number in st.session_state.courses_db[course]['quizzes']:
        st.write("Editar Quiz Existente")
        questions = st.session_state.courses_db[course]['quizzes'][lesson_number]
    else:
        st.write("Criar Novo Quiz")
        questions = [{"question": "", "answer": ""} for _ in range(5)]
    updated_questions = []
    for i, q in enumerate(questions):
        question = st.text_input(f"Pergunta {i+1}", value=q['question'])
        answer = st.text_input(f"Resposta {i+1}", value=q['answer'])
        if question and answer:
            updated_questions.append({"question": question, "answer": answer})
    if len(updated_questions) == 5 and st.button("💾 Salvar Quiz"):
        save_quiz(course, lesson_number, updated_questions)
        st.success(f"Quiz para a aula {lesson_number} salvo com sucesso!")

def show_student_courses(permissions):
    st.markdown('<p class="medium-font">Meus Cursos</p>', unsafe_allow_html=True)
    course_selection = st.selectbox('🎓 Selecione um curso', permissions)
    if course_selection:
        show_course_content(course_selection)

def show_course_content(course_selection):
    course = st.session_state.courses_db[course_selection]
    st.header(course['name'])
    st.write("📚 Tópicos do curso:")
    st.write(course['topics'])
    if 'progress' not in st.session_state.users_db[st.session_state.user_email]:
        st.session_state.users_db[st.session_state.user_email]['progress'] = {}
    if course_selection not in st.session_state.users_db[st.session_state.user_email]['progress']:
        st.session_state.users_db[st.session_state.user_email]['progress'][course_selection] = 1
    current_lesson = st.session_state.users_db[st.session_state.user_email]['progress'][course_selection]
    
    # Opção para voltar para aulas anteriores
    available_lessons = list(range(1, current_lesson + 1))
    selected_lesson = st.selectbox("📚 Selecione a aula", available_lessons, index=len(available_lessons)-1)
    
    if selected_lesson in course['lessons']:
        st.subheader(f"📚 Aula {selected_lesson}")
        lesson_content = course['lessons'][selected_lesson]   
        if 'video' in lesson_content:
            video_path = lesson_content['video']['file_path']
            st.video(video_path)
        if 'pdf' in lesson_content:
            pdf_path = lesson_content['pdf']['file_path']
            st.markdown(get_binary_file_downloader_html(pdf_path, lesson_content['pdf']['details']['FileName']), unsafe_allow_html=True)
        show_quiz(course_selection, selected_lesson)
    else:
        st.write("🎉 Você completou todas as aulas disponíveis!")
    
    # Opção para deixar feedback ao final do curso
    if current_lesson > len(course['lessons']):
        st.subheader("📝 Feedback do Curso")
        feedback = st.text_area("Por favor, deixe seu feedback sobre o curso:")
        if st.button("Enviar Feedback"):
            course['feedback'].append(feedback)
            st.success("Obrigado pelo seu feedback!")

def show_quiz(course_selection, current_lesson):
    if current_lesson in st.session_state.courses_db[course_selection]['quizzes']:
        st.subheader("❓ Quiz - Responda corretamente para desbloquear a próxima aula")
        user_answers = []
        for i, q in enumerate(st.session_state.courses_db[course_selection]['quizzes'][current_lesson]):
            user_answers.append(st.text_input(q['question'], key=f"quiz_{course_selection}_{current_lesson}_{i}"))
        if st.button("📝 Submeter Respostas"):
            results = check_quiz_answers(course_selection, current_lesson, user_answers)
            all_correct = all(results)
            for i, (question, is_correct) in enumerate(zip(st.session_state.courses_db[course_selection]['quizzes'][current_lesson], results)):
                if is_correct:
                    st.success(f"Pergunta {i+1}: Correta!")
                else:
                    st.error(f"Pergunta {i+1}: Incorreta. A resposta correta é: {question['answer']}")
            if all_correct:
                st.success("🎉 Parabéns! Você desbloqueou a próxima aula.")
                if current_lesson == st.session_state.users_db[st.session_state.user_email]['progress'][course_selection]:
                    st.session_state.users_db[st.session_state.user_email]['progress'][course_selection] += 1
                st.rerun()
            else:
                st.warning("⚠️ Algumas respostas estão incorretas. Revise o conteúdo e tente novamente!")

def show_student_progress(permissions):
    st.markdown('<p class="medium-font">Meu Progresso</p>', unsafe_allow_html=True)
    progress = st.session_state.users_db[st.session_state.user_email].get('progress', {})
    for course in permissions:
        if course in st.session_state.courses_db:
            current_lesson = progress.get(course, 1)
            total_lessons = len(st.session_state.courses_db[course]['lessons'])
            if total_lessons > 0:
                progress_percentage = min((current_lesson - 1) / total_lessons, 1.0)
                st.write(f"🎓 {st.session_state.courses_db[course]['name']}: Aula {current_lesson} de {total_lessons}")
                st.progress(progress_percentage)
            else:
                st.write(f"🎓 {st.session_state.courses_db[course]['name']}: Nenhuma aula disponível ainda.")

def show_help():
    st.markdown('<p class="medium-font">Ajuda</p>', unsafe_allow_html=True)
    st.write("""
    ℹ️ Como usar o sistema de cursos online:
    1. Cada curso é composto por aulas sequenciais.
    2. Você pode assistir a qualquer aula que já tenha sido desbloqueada.
    3. Após assistir a aula, você deve responder corretamente a um quiz de 5 perguntas.
    4. Se acertar todas as perguntas, você desbloqueará a próxima aula.
    5. Você pode baixar os PDFs das aulas, mas os vídeos não podem ser baixados.
    6. Cada aula tem seu próprio quiz independente.
    7. Você só tem acesso aos cursos que foram liberados para você pelo administrador.
    8. Ao final do curso, você pode deixar um feedback sobre sua experiência.
    
    Em caso de dúvidas, entre em contato com o suporte técnico.
    """)

if __name__ == '__main__':
    main()