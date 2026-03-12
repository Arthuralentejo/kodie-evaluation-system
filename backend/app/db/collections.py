from motor.motor_asyncio import AsyncIOMotorDatabase


def students_collection(db: AsyncIOMotorDatabase):
    return db["students"]


def questions_collection(db: AsyncIOMotorDatabase):
    return db["questions"]


def assessments_collection(db: AsyncIOMotorDatabase):
    return db["assessments"]


def answers_collection(db: AsyncIOMotorDatabase):
    return db["answers"]


def denylist_collection(db: AsyncIOMotorDatabase):
    return db["token_denylist"]


def auth_attempts_collection(db: AsyncIOMotorDatabase):
    return db["auth_attempts"]
