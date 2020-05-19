'''from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

chatbot = ChatBot('Nandi')

# Create a new trainer for the chatbot
trainer = ChatterBotCorpusTrainer(chatbot)

# Train the chatbot based on the english corpus
trainer.train("chatterbot.corpus.english")


#python -m spacy download en

trainer.train([
    	"Hello",
    	"Hi",
		"Hi there!",
		"How  are you doing?",
		"I'm doing great. How are you?",
		"I'm good."
		"That is good to hear",
		"Where do you live?",
		"I'm a bot, i can't live.",
		"Where you from?",
		"I'm a bot, built with python",
		"What is you name?",
		"I'm nandi",
		"Thank you.",
		"You are welcome.",
		"Tata",
		"Are you going, bye then."

])

'''
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer

# Create a new chat bot named Charlie
chatbot = ChatBot('Nandi')

trainer = ListTrainer(chatbot)




while True:
        message  = input('You : ')
        if message.strip() != 'Bye':	
            reply = chatbot.get_response(message)
            print('Nandi : ',reply)
        if message.strip() == 'Bye':
        	print('Nandi : Bye ')
        	break 