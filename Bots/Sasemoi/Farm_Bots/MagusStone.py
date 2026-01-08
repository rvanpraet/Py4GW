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
    upkeep_alcohol_active=True,
    upkeep_alcohol_target_drunk_level=1,
    config_log_actions=False
)

# hero_list = [
#     HeroType.Gwen,
#     HeroType.MOX,
#     HeroType.Melonni
# ]

# hero_template_list = [
#     (HeroType.Gwen, "OQpjAwDjKP3XlAAAAAAAAAAAAA"),
#     (HeroType.MOX, "Ogmioys8cfpxAAAAAAAAAAAA"),
#     (HeroType.Melonni, "Ogmioys8cfpxAAAAAAAAAAAA")
# ]

def create_bot_routine(bot: Botting) -> None:
    InitBot(bot)
    SetupResign(bot)
    MagusStoneRoutine(bot)


def InitBot(bot: Botting) -> None:
    bot.States.AddHeader("Init Party")
    bot.Map.Travel(RATA_SUM)
    # MysticHealingSupport.SetupHealingParty(bot, hero_list=hero_template_list)

def SetupResign(bot: Botting):
    bot.States.AddHeader("Setup Resign")
    bot.Move.XYAndExitMap(16387.96, 13047.04, target_map_id=MAGUS_STONE) # target_map_name="Barbarous Shore"
    bot.Wait.ForTime(350)
    bot.Move.XYAndExitMap(16094, 14417, target_map_id=RATA_SUM) # target_map_name="Camp Hojanu"


def MagusStoneRoutine(bot: Botting) -> None:
    bot.States.AddHeader("Running Routine")
    bot.Move.XYAndExitMap(16387.96, 13047.04, target_map_id=MAGUS_STONE) # target_map_name="Barbarous Shore"
    # MysticHealingSupport.InitHeroComanagedRoutines(bot, hero_list=hero_list)

    # bot.Party.FlagAllHeroes(17070.32, 12985.33)

    bot.Move.FollowPath(path, "Magus Stone Farming Path")




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

path = [
    #normal running routine
    (17561.23, 7616.28), # Before first spider group
    (19078.75, 4208.01), # After first spider group

    #balling running routine
    (18951.85, 3844.59), # First back n forth to ball spider group 1
    (18470.39, 3916.44),
    (18951.85, 3844.59), # Second back n forth to ball spider group 2
    (18470.39, 3916.44),
    #start killing routine
    #kill spiders

    #path2
    (17911.47, 1191.82), # Leaving after killing first group to before narrow path
    (17665.95, 185.75), # Hug left side of narrow path
    (17279.21, -687.44), # After narrow path


    (17308.99, -2487.48), # First back n forth to ball spider group 2
    (16785.13, -2110.67),
    (17308.99, -2487.48), # Second back n forth to ball spider group 2
    (16785.13, -2110.67),
]


path_2 = [

  # (17313.97, -2603.54),
]