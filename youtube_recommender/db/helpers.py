""" helpers.py 

    helper methods for SQLAlchemy models, listed in models.py
"""

from typing import Any, Optional  # Dict, Set, List, Tuple

from sqlalchemy.future import select

from rarc_utils.sqlalchemy_base import create_many
from rarc_utils.sqlalchemy_base import get_str_mappings as get_str_mappings_custom
from rarc_utils.sqlalchemy_base import aget_str_mappings as aget_str_mappings_custom

# async def aget_all(asession, model, skip: int = 0, limit: int = 100):
async def aget_all(session, model=None, skip: int = 0, limit: int = 100):
    """generic method to get all items for a model

    loop.run_until_complete(run_in_session(async_session, aget_all, model=Habbit))
    loop.run_until_complete(run_in_session(async_session, aget_all, model=genericTask))
    """
    assert model is not None
    # async with asession() as session:
    query = select(model).offset(skip).limit(limit)
    res = await session.execute(query)
    return list(res.scalars())


async def aget_all_by_userid(
    session, model, user_id: int, skip: int = 0, limit: int = 100
):
    """generic method to get all items for a model for given user_id

    loop.run_until_complete(run_in_session(async_session, aget_all_by_userid, model=Activity, user_id=2))
    """
    # async with asession() as session:
    query = (
        select(model).filter_by(user_id=user_id).offset(skip).limit(limit)
    )  # .join(Habbit, Habbit.id == Activity.habbit_id)
    res = await session.execute(query)
    return list(res.scalars())


async def aget_by_name(session, model, name: str) -> Optional[Any]:
    """generic method to get item for a given model by name
    used to search for items

    loop.run_until_complete(run_in_session(async_session, aget_by_name, model=genericTask, name='read'))
    """
    # async with asession() as session:
    query = select(model).filter_by(name=name).limit(1)
    res = (await session.execute(query)).first()
    if res is not None:
        return res[0]
    return res


# str_mappings = loop.run_until_complete(aget_str_mappings(psql))
async def aget_str_mappings(psqConfig, models=()):

    return await aget_str_mappings_custom(psqConfig, models)


# str_mappings = get_str_mappings(s)
def get_str_mappings(psqConfig, models=()):

    return get_str_mappings_custom(psqConfig, models)


async def create_many_items(asession, model, itemDicts, nameAttr="name", returnExisting=False):

    async with asession() as session:
        items = await create_many(session, model, itemDicts, nameAttr=nameAttr, returnExisting=returnExisting)

    return items


def get_all(session, model):
    """get all items of a model
    example usage:
        tasks = get_all(psession, Task)
        habbits = get_all(psession, Habbit)
    """
    stmt = select(model).filter()
    return list(session.execute(stmt).scalars())
