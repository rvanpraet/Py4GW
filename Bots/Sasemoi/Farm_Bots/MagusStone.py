from typing import Iterable
import Py4GW
from Py4GWCoreLib import Agent, Routines, ConsoleLog, Console
from Py4GWCoreLib import ThrottledTimer
from Py4GWCoreLib import GLOBAL_CACHE, Map
from Py4GWCoreLib import Botting, HeroType
from Bots.Sasemoi.bot_helpers.bot_mystic_healing_support import MysticHealingSupport
from Py4GWCoreLib.Builds.BuildHelpers.BuildDangerHelper import DangerTable
from Py4GWCoreLib.Builds.DervSpiderFarmer import DervBuildFarmStatus, DervSpiderFarmer
from Py4GWCoreLib.enums_src.GameData_enums import Range
from Py4GWCoreLib.Builds.BuildHelpers import BuildDangerHelper

RATA_SUM = 640
MAGUS_STONE = 569
SCRIPT_NAME = "Magus Stone Derv Farm Bot"
SPIDER_MODEL = 6846
FOES_MODEL_IDS = [SPIDER_MODEL]

magus_stone_cripple_danger_table: DangerTable = (
    ([6479, 6383, 6382], "Spider"),
)

bot = Botting(
    SCRIPT_NAME,
    custom_build=DervSpiderFarmer(
        build_danger_helper=BuildDangerHelper(
            cripple_kd_table=magus_stone_cripple_danger_table,
        )
    ),
    upkeep_hero_ai_active=False,
    upkeep_auto_combat_active=False,
    upkeep_auto_inventory_management_active=False,
    upkeep_auto_loot_active=False,
    upkeep_alcohol_active=False,
    upkeep_alcohol_target_drunk_level=1,
    config_log_actions=False,
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

#region routines
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
    bot.Wait.ForMapLoad(MAGUS_STONE)
    # MysticHealingSupport.InitHeroComanagedRoutines(bot, hero_list=hero_list)
    # bot.Party.FlagAllHeroes(17070.32, 12985.33)

    # Set combat routine
    # bot.config.set_pause_on_danger_fn(detect_spider_or_loot)
    bot.Properties.Enable('alcohol')
    bot.Properties.Enable('auto_combat')
    bot.Wait.ForTime(5000) # Wait for buffs to cast

    # bot.Properties.Enable("pause_on_danger")

    for x,y,status in path:
        bot.Move.XY(x, y)
        bot.States.AddCustomState(lambda: set_bot_status(bot, status), f"Set Build Status to {status}")

    ConsoleLog(SCRIPT_NAME, "Insert looting logic here", Py4GW.Console.MessageType.Info)

    for x,y,status in path_2:
        bot.Move.XY(x, y)
        bot.States.AddCustomState(lambda: set_bot_status(bot, status), f"Set Build Status to {status}")
    
    bot.Wait.ForTime(1000)
    bot.Party.Resign()


#region main methods
def set_bot_status(bot: Botting, status: str) -> None:
    '''Sets the bot's build status to the specified status.'''
    build = bot.config.build_handler
    if build is not None and isinstance(build, DervSpiderFarmer):
        build.status = status

    ConsoleLog(SCRIPT_NAME, f"Setting bot status to: {status}", Py4GW.Console.MessageType.Info)


def detect_enemy_or_loot():
    '''Detects if there are any enemies or viable loot in the vicinity.'''
    global item_id_blacklist

    build = bot.config.build_handler
    if isinstance(build, DervSpiderFarmer) and build.status not in [DervBuildFarmStatus.Kill, DervBuildFarmStatus.Loot]:
        return False

    enemy_array = get_enemy_array(custom_range=Range.Earshot.value)
    if enemy_array:
        return True

    # filtered_agent_ids = get_valid_loot_array(viable_loot=[])
    # if not filtered_agent_ids:
    #     return False

    # filtered_agent_ids = [agent_id for agent_id in filtered_agent_ids if agent_id not in set(item_id_blacklist)]

    # if not filtered_agent_ids:
    #     return False

    # return True


#region helper methods
def get_enemy_array(custom_range = Range.Area.value * 1.50, detectable_collection: Iterable[int] = []) -> list[int]:
    px, py = GLOBAL_CACHE.Player.GetXY()
    enemy_array = Routines.Agents.GetFilteredEnemyArray(px, py, custom_range)
    return [
        agent_id
        for agent_id in enemy_array
        if Agent.GetModelID(agent_id) in detectable_collection
    ]

def get_valid_loot_array(viable_loot=[]):
    pass

#region main
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
    (17561.23, 7616.28, DervBuildFarmStatus.Move), # Before first spider group
    (19078.75, 4208.01, DervBuildFarmStatus.Move), # After first spider group

    #balling running routine
    (19004.04, 3309.77, DervBuildFarmStatus.Ball), # First back n forth to ball spider group 1
    (18356.18, 3276.71, DervBuildFarmStatus.Ball),
    (19004.04, 3309.77, DervBuildFarmStatus.Ball), # Second back n forth to ball spider group 2
    (18356.18, 3276.71, DervBuildFarmStatus.Kill),


    # (18470.39, 3916.44, DervBuildFarmStatus.Kill), # Backup
    #kill spiders
    #loot
]

path_2  = [
    (17911.47, 1191.82, DervBuildFarmStatus.Move), # Leaving after killing first group to before narrow path

    # Insert back and forth to clear the narrow path
    (17580.91, 844.03, DervBuildFarmStatus.Move), # Maybe wait here for a bit
    (17952.61, 1345.80, DervBuildFarmStatus.Move),

    (17665.95, 185.75, DervBuildFarmStatus.Move), # Hug left side of narrow path
    (17560.50, -342.79, DervBuildFarmStatus.Move), # More left side of narrow path
    (17279.21, -687.44, DervBuildFarmStatus.Move), # After narrow path


    (17543.69, -3031.16, DervBuildFarmStatus.Move), # First back n forth to ball spider group 2
    (17221.04, -3275.86, DervBuildFarmStatus.Ball), # 
    (17543.69, -3031.16, DervBuildFarmStatus.Move), # Second back n forth to ball spider group 2
    (16925.17, -2726.17, DervBuildFarmStatus.Kill), # Last stop before killing routine

    #kill spiders
    #loot


    # (17308.99, -2487.48, DervBuildFarmStatus.Ball), # First back n forth to ball spider group 2
    # (16785.13, -2110.67, DervBuildFarmStatus.Ball),
    # (17308.99, -2487.48, DervBuildFarmStatus.Ball), # Second back n forth to ball spider group 2
    # (16785.13, -2110.67, DervBuildFarmStatus.Kill),

]