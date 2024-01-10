import json
import dotenv
import telebot
from telebot import async_telebot, util
import asyncio
from questions import questions

token = dotenv.get_key('.env', 'TELEGRAM_BOT_TOKEN')

bot = telebot.async_telebot.AsyncTeleBot(token)

checked = False


class Question:
    def __init__(self, question: str, answers: list[str]):
        self.question = question
        self.answers = answers
        self.question_number = take_only_nums(question[:4])
        self.current_answer = ''  # В этой строке будет только буква ответа


def load_data():
    try:
        with open("users.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return {}


def save_data(data: dict):
    with open('users.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def take_only_nums(string: str):
    result = ''
    for char in string:
        try:
            int(char)
            result += char
        except:
            continue
    return int(result)


def gen_markup(question: Question) -> telebot.types.InlineKeyboardMarkup:
    return util.quick_markup({
        f'{question.answers[0][0:4].rstrip()}': {'callback_data': f'{question.answers[0][0:4].rstrip()}'},
        f'{question.answers[1][0:4].rstrip()}': {'callback_data': f'{question.answers[1][0:4].rstrip()}'},
        f'{question.answers[2][0:4].rstrip()}': {'callback_data': f'{question.answers[2][0:4].rstrip()}'}
    })


async def check_answers(call: telebot.types.CallbackQuery, msg_sent):
    global checked
    data = load_data()
    if '' not in data[str(call.from_user.id)].values() and msg_sent == 15 and not checked:
        await bot.send_message(call.from_user.id, 'Вы ответили на все вопросы! Подтверждаете свой выбор?',
                               reply_markup=confirm_keyboard)
        checked = True


start_keyboard_1 = util.quick_markup({'Начать': {'callback_data': 'init'}})
start_keyboard_2 = util.quick_markup({
    'Пройти снова': {'callback_data': 'init'},
    'Продолжить': {'callback_data': 'keep_answering'}
})
confirm_keyboard = util.quick_markup({'Подтвердить': {'callback_data': 'confirm'}})
user_data: dict = load_data()
messages_sent = 0


@bot.message_handler(commands=['start', 'help'])
async def hello(message: telebot.types.Message):
    if message.text == '/start':
        if str(message.chat.id) not in user_data:
            text = 'Здравствуйте! Добро пожаловать в бота-анкету. Нажмите "Начать" чтобы начать опрос'
            kb = start_keyboard_1

        else:
            text = ('Снова добро пожаловать! Чтобы начать заново нажмите на "Пройти снова", чтобы продолжить с '
                    'сохраненными ответами нажмите "продолжить"')
            kb = start_keyboard_2
        await bot.send_message(message.chat.id, text, reply_markup=kb)
    else:
        await bot.send_message(message.chat.id, 'Данный бот создан чтобы дать вам пройти тест на степень вашего '
                                                'оптимизма. Чтобы сменить ответ вы можете просто нажать на нужную '
                                                'кнопку под сообщением. Это сработает на прошлом сообщении даже после '
                                                'отправки нового вопроса. Рекомендую не нажимать на кнопку "Начать" '
                                                'несколько раз. Это запустит несколько анкет одновременно')


@bot.callback_query_handler(func=lambda call: True)
async def init_questionnaire(call: telebot.types.CallbackQuery):
    global messages_sent
    new_questions: list[Question] = []
    for quest in questions:
        new_questions.append(Question(quest, questions[quest]))
    if call.data == 'confirm':
        coefficients = {
            'a': 2,
            'b': 4,
            'c': 6
        }
        total = 0
        print(user_data[str(call.from_user.id)].values())
        for i in user_data[str(call.from_user.id)].values():
            total += coefficients[i]
        if total < 30:
            text = 'У вас низкий уровень оптимизма'
        elif total < 50:
            text = 'У вас средний уровень оптимизма!'
        else:
            text = 'У вас высокий уровень оптимизма'
        await bot.send_message(call.from_user.id, text,
                               reply_markup=util.quick_markup({'Пройти снова': {'callback_data': 'init'}}))
        return
    elif call.data == 'init':
        global checked
        checked = False
        messages_sent = 0
        for question in new_questions:
            user_data[str(call.from_user.id)] = {}
            user_data[str(call.from_user.id)][str(question.question_number)] = ''
            text = f'{question.question}\n{question.answers[0]}\n{question.answers[1]}\n{question.answers[2]}\n'
            messages_sent += 1
            await bot.send_message(call.from_user.id, text, reply_markup=gen_markup(question))
            await asyncio.sleep(5)

        save_data(user_data)
        await check_answers(call, messages_sent)
    elif call.data == 'keep_answering':
        checked = False
        messages_sent = 0
        for question in new_questions:
            try:
                question.current_answer = user_data[str(call.from_user.id)][str(question.question_number)]
                text = f'{question.question}\n{question.answers[0]}\n{question.answers[1]}\n{question.answers[2]}\nТекущий ответ: {question.current_answer}'
            except:
                question.current_answer = ''
                text = f'{question.question}\n{question.answers[0]}\n{question.answers[1]}\n{question.answers[2]}'
            messages_sent += 1
            await bot.send_message(call.from_user.id, text, reply_markup=gen_markup(question))
            await asyncio.sleep(5)

            await check_answers(call, messages_sent)
    else:
        question = new_questions[take_only_nums(call.data) - 1]
        question.current_answer = call.data[-2]
        user_data[str(call.from_user.id)][str(question.question_number)] = question.current_answer
        save_data(user_data)
        try:
            text = f'{question.question}\n{question.answers[0]}\n{question.answers[1]}\n{question.answers[2]}\nТекущий ответ: {question.current_answer}'
            await bot.edit_message_text(message_id=call.message.id, chat_id=call.from_user.id,
                                        text=text,
                                        reply_markup=call.message.reply_markup)
        except:
            pass
        user_data[str(call.from_user.id)].values()
        await check_answers(call, messages_sent)


@bot.message_handler()
async def handle_unexpected(message: telebot.types.Message):
    await bot.send_message(message.from_user.id, '')


asyncio.run(bot.polling(non_stop=True))
