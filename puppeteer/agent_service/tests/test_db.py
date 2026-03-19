import pytest
from agent_service.db import User, Node, Job
from sqlalchemy.future import select

@pytest.mark.anyio
async def test_user_model(db_session):
    user = User(username="testuser", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.username == "testuser"))
    fetched_user = result.scalar_one()
    assert fetched_user.username == "testuser"

@pytest.mark.anyio
async def test_node_model(db_session):
    node = Node(node_id="n1", hostname="h1", ip="1.1.1.1", status="ONLINE")
    db_session.add(node)
    await db_session.commit()
    
    result = await db_session.execute(select(Node).where(Node.node_id == "n1"))
    fetched_node = result.scalar_one()
    assert fetched_node.hostname == "h1"
