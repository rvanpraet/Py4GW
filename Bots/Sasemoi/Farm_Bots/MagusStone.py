import Py4GW
from Py4GWCoreLib import Routines, ConsoleLog, Console
from Py4GWCoreLib import ThrottledTimer
from Py4GWCoreLib import GLOBAL_CACHE, Map
from Py4GWCoreLib import Botting, HeroType
from Bots.Sasemoi.bot_helpers.bot_mystic_healing_support import MysticHealingSupport

RATA_SUM = 640
MAGUS_STONE = 569

bot = Botting(
    "Heroes Test Bot",
    upkeep_hero_ai_active=False,
    upkeep_auto_combat_active=False,
    upkeep_auto_inventory_management_active=False,
    upkeep_auto_loot_active=False,
    config_log_actions=False
)

hero_list = [
    HeroType.Gwen,
    HeroType.MOX,
    HeroType.Melonni
]

hero_template_list = [
    (HeroType.Gwen, "OQpjAwDjKP3XlAAAAAAAAAAAAA"),
    (HeroType.MOX, "Ogmioys8cfpxAAAAAAAAAAAA"),
    (HeroType.Melonni, "Ogmioys8cfpxAAAAAAAAAAAA")
]

def create_bot_routine(bot: Botting) -> None:
    InitBot(bot)
    SetupResign(bot)
    MagusStoneRoutine(bot)


def InitBot(bot: Botting) -> None:
    bot.States.AddHeader("Init Party")
    MysticHealingSupport.SetupHealingParty(bot, hero_list=hero_template_list)

def SetupResign(bot: Botting):
    bot.States.AddHeader("Setup Resign")
    bot.Move.XYAndExitMap(16387.96, 13047.04, target_map_id=MAGUS_STONE) # target_map_name="Barbarous Shore"
    bot.Wait.ForTime(350)
    bot.Move.XYAndExitMap(16094, 14417, target_map_id=RATA_SUM) # target_map_name="Camp Hojanu"


def MagusStoneRoutine(bot: Botting) -> None:
    bot.States.AddHeader("Launch Bots")
    MysticHealingSupport.InitHeroComanagedRoutines(bot, hero_list=hero_list)

    bot.Party.FlagAllHeroes(17070.32, 12985.33)
    bot.Move.XY(17328.93, 7559.94) # Before first spider group

    bot.Properties.Enable('hero_ai')
    bot.States.AddCustomState(lambda: KeepRunning(), "Keep Bot Running")
    bot.States.AddCustomState(lambda: KeepRunning(), "Another state to keep running")

def KeepRunning():
    while True:
        yield from Routines.Yield.wait(100)



bot.SetMainRoutine(create_bot_routine)
base_path = Console.get_projects_path()


def configure():
    global bot
    bot.UI.draw_configure_window()

def main():
    bot.Update()
    projects_path = Console.get_projects_path()
    widgets_path = projects_path + "\\Widgets\\Config\\textures\\"
    bot.UI.draw_window(icon_path=widgets_path + "YAVB 2.0 mascot.png")

if __name__ == "__main__":
    main()