import os
from dotenv import load_dotenv
import sys

load_dotenv()
WORKDIR=os.getenv("WORKDIR")
os.chdir(WORKDIR)
sys.path.append(WORKDIR)

from langgraph.graph import StateGraph
from src.utils import State, GraphInput, GraphOutput, GraphConfig
from src.nodes import *
from src.routers import *


workflow = StateGraph(State, 
                      input = GraphInput,
                      output = GraphOutput,
                      config_schema = GraphConfig)

workflow.add_node("instructor", get_clear_instructions)
workflow.set_entry_point("instructor")
workflow.add_node("human_feedback", read_human_feedback)
workflow.add_node("brainstorming_writer", making_writer_brainstorming)
workflow.add_node("brainstorming_critique", brainstorming_critique)
workflow.add_node("writer", generate_content)
workflow.add_conditional_edges(
    "instructor",
    should_go_to_brainstorming_writer
)
workflow.add_edge("human_feedback","instructor")
workflow.add_conditional_edges(
    "brainstorming_writer",
    should_continue_with_critique
)

workflow.add_edge("brainstorming_critique","brainstorming_writer")
workflow.add_conditional_edges(
    "writer",
    has_writer_ended_book
)

app = workflow.compile(
    interrupt_before=['human_feedback']
    )


if __name__ == '__main__':
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.memory import MemorySaver
    app = workflow.compile(
        interrupt_before=['human_feedback'],
        checkpointer=MemorySaver()
    )

    human_input_msg = "An unexpected crime story centered around an assassination, featuring various suspects throughout the narrative, with a final plot twist where the guilty party is not recognized until the end. The book targets young adults and emphasizes themes of suspense and unpredictability, written in a style similar to Stephen King."
    
    configuration = {
        "configurable": {
            "thread_id": 42,
            "language":"spanish",
            "instructor_model":"meta",
            "brainstormer_model":"meta",
            "critique_model":"openai",
            "writer_model":"openai"
        }
    }

    for event in app.stream(
            input = {'user_instructor_messages': [HumanMessage(content=human_input_msg)]},
            config = configuration,
            stream_mode='values'):
        

        event['user_instructor_messages'][-1].pretty_print()

    
    while True:
        new_human_input_msg = input("Provide your answer: ")
        new_human_input_msg = HumanMessage(content = new_human_input_msg)
        app.update_state(configuration, {'user_instructor_messages': [new_human_input_msg]}, as_node = 'human_feedback')
        new_human_input_msg.pretty_print()
        current_node = 'human_feedback'
        app.get_state(config = configuration).next
        for event in app.stream(
                input = None,
                config = configuration,
                stream_mode='values'):
            print('---')
            if (current_node == 'human_feedback'):
                event['user_instructor_messages'][-1].pretty_print()
            if (current_node == 'instructor'):
                if event['user_instructor_messages'][-1].type == 'human':
                    AIMessage(content = str(event['instructor_documents'])).pretty_print()
                else:
                    event['user_instructor_messages'][-1].pretty_print()

            #PEDING FOR ALL THE COMBINATIONS
            current_node = app.get_state(config = configuration).next[0]
            print('---')
