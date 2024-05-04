from environs import Env
from dataclasses import dataclass

#settings
@dataclass
class Bots:
    bot_token: str
    admin_id: int
    admin_id_2: int
    admin_id_3: int

@dataclass
class Settings:
    bots: Bots

def get_settings(path: str):
    env = Env()
    env.read_env(path)

    return Settings(
        bots=Bots(
            bot_token=env.str("TOKEN"),
            admin_id=env.int("MAIN_ADMIN_ID"),
            admin_id_2=env.int("ADMIN"),
            admin_id_3=env.int("ADMIN2")
        )
    )

settings = get_settings('input')
# print settings
#print(settings)