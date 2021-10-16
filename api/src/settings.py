from environ import Env

env = Env()
env.read_env()

MONGODB_URL = env("MONGODB_URL", cast=str, default="mongodb://localhost:27017")
