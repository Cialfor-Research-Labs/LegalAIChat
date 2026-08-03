from app.routes.chat import ChatRequest


def test_chat_request_accepts_optional_context_fields():
    request = ChatRequest(
        query="What remedy is available?",
        session_id="session-1",
        matter_id="matter-1",
        personalization={"baseStyle": "Concise", "memoryEnabled": True},
    )

    assert request.matter_id == "matter-1"
    assert request.personalization == {
        "baseStyle": "Concise",
        "memoryEnabled": True,
    }


def test_chat_request_context_fields_are_optional():
    request = ChatRequest(query="Explain bail")

    assert request.matter_id is None
    assert request.personalization is None
