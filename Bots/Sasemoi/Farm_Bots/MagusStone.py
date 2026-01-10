import Py4GW
from math import floor, cos, sin, pi
from typing import Iterable
from Bots.Sasemoi.bot_helpers.bot_stuck_helper import BotStuckHelper
from Bots.Sasemoi.utils.loot_filter_utils.magus_stone_loot_filters import get_valid_loot_array
from Bots.marks_coding_corner.utils.loot_utils import is_valid_item
from Py4GWCoreLib import Agent, AgentArray, Item, Routines, ConsoleLog, Console
from Py4GWCoreLib import ThrottledTimer
from Py4GWCoreLib import GLOBAL_CACHE, Map
from Py4GWCoreLib import Botting, HeroType
from Bots.Sasemoi.bot_helpers.bot_mystic_healing_support import MysticHealingSupport
from Py4GWCoreLib.Builds.BuildHelpers.BuildDangerHelper import DangerTable
from Py4GWCoreLib.Builds.DervSpiderFarmer import DervBuildFarmStatus, DervSpiderFarmer
from Py4GWCoreLib.enums_src.GameData_enums import Range
from Py4GWCoreLib.Builds.BuildHelpers import BuildDangerHelper
from Py4GWCoreLib.enums_src.Model_enums import ModelID
from Py4GWCoreLib.py4gwcorelib_src import Utils
from Py4GWCoreLib.py4gwcorelib_src.ActionQueue import ActionQueueManager

TIMEOUT_MS = 30000
RATA_SUM = 640
MAGUS_STONE = 569
SCRIPT_NAME = "Magus Stone Derv Farm Bot"
SPIDER_MODEL = 6846
FOES_MODEL_IDS = [SPIDER_MODEL]

magus_stone_cripple_danger_table: DangerTable = (
    ([6479, 6383, 6382], "Spider"),
)

# Global states

is_farming = False
is_looting = False
item_id_blacklist: list[int] = []

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


# Custom stuck scenario for Magus Stone Derv Farm Bot
is_movement_stuck = False
custom_stuck_scenario = (
    "Magus Stone Stuck Handler",
    lambda bot=bot: movement_stuck_condition_fn(bot),
    lambda: handle_movement_stuck()
)

# Would like to move this to Botting
stuck_helper = BotStuckHelper(
    config={
        "log_enabled": False,
        "movement_timeout_ms": TIMEOUT_MS,
        "movement_timeout_handler": lambda: handle_stuck(),
        "custom_scenarios": [custom_stuck_scenario],
        "movement_not_moved_distance": 100
    }
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






# ==================== ROUTINE METHODS ==================== #

#region routines
def create_bot_routine(bot: Botting) -> None:
    InitBot(bot)
    SetupResign(bot)
    MagusStoneRoutine(bot)
    ResetFarmLoop(bot)


def InitBot(bot: Botting) -> None:
    bot.States.AddHeader("Init Party")
    bot.Map.Travel(RATA_SUM)

    # Death callback
    condition = lambda: on_death(bot)
    bot.Events.OnDeathCallback(condition)
    bot.Properties.Enable("halt_on_death")
    bot.Properties.Disable("auto_loot")
    bot.Properties.Disable("hero_ai")
    bot.Properties.Disable("auto_combat")
    bot.Properties.Disable("pause_on_danger")

    bot.States.AddCustomState(lambda: EquipSkillBar(bot), "Equip Skill Bar")

    # MysticHealingSupport.SetupHealingParty(bot, hero_list=hero_template_list)

def SetupResign(bot: Botting):
    bot.States.AddHeader("Setup Resign")
    bot.Move.XYAndExitMap(16387.96, 13047.04, target_map_id=MAGUS_STONE) # target_map_name="Barbarous Shore"
    bot.Wait.ForTime(350)
    bot.Move.XYAndExitMap(16094, 14417, target_map_id=RATA_SUM) # target_map_name="Camp Hojanu"


def MagusStoneRoutine(bot: Botting) -> None:
    bot.States.AddHeader("Running Routine")
    bot.States.AddCustomState(lambda: set_bot_status(bot, DervBuildFarmStatus.Setup), "Set Build Status to Setup")
    bot.Move.XYAndExitMap(16387.96, 13047.04, target_map_id=MAGUS_STONE) # target_map_name="Barbarous Shore"
    bot.Wait.ForMapLoad(MAGUS_STONE)
    # MysticHealingSupport.InitHeroComanagedRoutines(bot, hero_list=hero_list)
    # bot.Party.FlagAllHeroes(17070.32, 12985.33)

    # Set combat routine
    bot.config.set_pause_on_danger_fn(pause_on_danger_fn)
    bot.States.AddCustomState(lambda: stuck_helper.Toggle(True), "Activate Stuck Helper")
    bot.States.AddManagedCoroutine("Run Stuck Handler", run_stuck_helper)
    bot.States.AddManagedCoroutine("Setup loot handler", lambda: handle_loot(bot))
    bot.States.AddCustomState(lambda: use_alcohol(), "Use Alcohol")
    bot.Properties.Enable('auto_combat')
    bot.Properties.Enable('pause_on_danger')
    bot.Wait.ForTime(3000) # Wait for buffs to cast

    # bot.Properties.Enable("pause_on_danger")

    # Follow the path
    for x,y,status,wait_time in path_1:
        bot.Move.XY(x, y)
        bot.States.AddCustomState(lambda bot=bot, status=status: set_bot_status(bot, status), f"Set Build Status to {status}")
        bot.Wait.ForTime(wait_time)

    # Execute farm routine
    bot.States.AddCustomState(lambda: execute_farm_routine(bot), "Execute Farm Routine 1")

    # Second part of the path
    for x,y,status,wait_time in path_2:
        bot.Move.XY(x, y)
        bot.States.AddCustomState(lambda bot=bot, status=status: set_bot_status(bot, status), f"Set Build Status to {status}")
        bot.Wait.ForTime(wait_time)
    
    # Execute farm routine
    bot.States.AddCustomState(lambda: execute_farm_routine(bot), "Execute Farm Routine 1")
    bot.Wait.ForTime(1000)
    bot.States.AddCustomState(lambda: set_bot_status(bot, DervBuildFarmStatus.Wait), "Waiting to return")
    bot.States.AddCustomState(lambda: wait_for_loot_to_finish(), "Wait for loot to finish")


# Reset the farm loop to run Magus Stone farm again
def ResetFarmLoop(bot: Botting):
    bot.States.AddHeader("Reset Farm Loop")
    bot.Properties.Disable("auto_combat")
    bot.States.AddCustomState(lambda: stuck_helper.Toggle(False), "Deactivate Stuck Helper")
    bot.States.RemoveManagedCoroutine("Run Stuck Handler")

    # MysticHealingSupport.RemoveHeroComanagedRoutines(bot, hero_list=hero_list)
    bot.States.AddCustomState(reset_item_blacklist, "Reset Opened Chests List")


    bot.Party.Resign()
    bot.Wait.ForTime(3000)
    bot.Wait.UntilCondition(lambda: Agent.IsDead(GLOBAL_CACHE.Player.GetAgentID()))
    # bot.States.AddCustomState(lambda: AssessLootManagement(), "Loot management check")
    # bot.Wait.ForTime(10000)
    # bot.States.AddCustomState(lambda: ConditionallyMoveToMerchant(), "Move to merchant for inventory check")
    # bot.States.AddCustomState(lambda: ManageInventory(bot), "Manage management execution")
    # bot.States.JumpToStepName("[H]Barbarous Shore Running_6")




# ==================== GENERAL SCRIPT METHODS ==================== #

#region main methods
# On Death Callback Routine
def _on_death(bot: Botting):
    yield from Routines.Yield.wait(1000)
    yield from Routines.Yield.Player.Resign()
    yield from reset_item_blacklist()
    yield from Routines.Yield.wait(10000)  # Wait for death to complete

    fsm = bot.config.FSM
    fsm.jump_to_state_by_name("[H]Running Routine_3") 
    fsm.resume()                           
    yield  


def on_death(bot: Botting):
    ConsoleLog("Death detected", "Player Died - Run Failed, Restarting...", Py4GW.Console.MessageType.Notice)

    # Reset Action Queues and FSM
    ActionQueueManager().ResetAllQueues()
    fsm = bot.config.FSM
    fsm.pause()
    fsm.RemoveManagedCoroutine("Run Stuck Handler")
    fsm.AddManagedCoroutine("OnDeath", _on_death(bot))


def run_stuck_helper():
    global is_movement_stuck

    is_movement_stuck = False
    yield from stuck_helper.Run()


# Ultimate stuck handler which resigns
def handle_stuck():
    yield from Routines.Yield.Player.Resign()
    yield from Routines.Yield.wait(500)


# Condition function for executing the early stuck movement helper
def movement_stuck_condition_fn(bot: Botting):
    global is_movement_stuck
    global stuck_helper

    return (
        Map.GetMapID() == MAGUS_STONE and # Only in Magus Stone
        not is_movement_stuck and # Not already stuck
        isinstance(bot.config.build_handler, DervSpiderFarmer) and
        bot.config.build_handler.status in [DervBuildFarmStatus.Move, DervBuildFarmStatus.Loot, DervBuildFarmStatus.Kill] and
        not Agent.IsAttacking(GLOBAL_CACHE.Player.GetAgentID()) and
        stuck_helper.movement_stuck_time / TIMEOUT_MS >= 0.15 # around 5 seconds of stuck time
    )


# Stuck handler which tries to move back and wiggle to unstuck
def handle_movement_stuck():
    global is_movement_stuck
    global stuck_helper

    # Dont execute if already stuck and running this fn
    if is_movement_stuck:
        yield None
        return
    
    is_movement_stuck = True

    # Calculate backpedal position
    player_pos = GLOBAL_CACHE.Player.GetXY()
    facing_direction = Agent.GetRotationAngle(GLOBAL_CACHE.Player.GetAgentID())
    back_angle = facing_direction + pi  # 180° behind
    back_distance = 200
    back_offset_x = cos(back_angle) * back_distance
    back_offset_y = sin(back_angle) * back_distance
    back_x, back_y = (player_pos[0] + back_offset_x, player_pos[1] + back_offset_y)

    # 2 seconds of movement unstuck attempts
    attempt_timer = ThrottledTimer(2000)
    attempt_timer.Start()
    GLOBAL_CACHE.Player.SendChatCommand("stuck")

    # Try to unstuck for 10 seconds
    while not attempt_timer.IsExpired():
        # Break early if map invalid or dead
        if not Routines.Checks.Map.MapValid() or Agent.IsDead(GLOBAL_CACHE.Player.GetAgentID()):
            ConsoleLog(SCRIPT_NAME, "Map invalid or player dead, breaking movement stuck loop", Py4GW.Console.MessageType.Debug)
            # is_movement_stuck = False
            yield None
            break

        # Break early if no longer stuck
        if stuck_helper.movement_stuck_time < 1000:
            ConsoleLog(SCRIPT_NAME, "Movement unstuck successful, resuming normal operation", Py4GW.Console.MessageType.Debug)
            # is_movement_stuck = False
            yield None
            break

        # Move to backwards position
        for _ in range(9):
            GLOBAL_CACHE.Player.Move(back_x, back_y)
            # yield from Routines.Yield.wait(100)
        
        # Strafe left/right to wiggle
        time_left = floor(attempt_timer.GetTimeRemaining() / 1000)
        if time_left % 2 == 0:
            yield from Routines.Yield.Movement.StrafeLeft(1000)
        else : 
            yield from Routines.Yield.Movement.StrafeRight(1000)


    ConsoleLog(SCRIPT_NAME, "Unstuck attempts complete", Py4GW.Console.MessageType.Debug)
    is_movement_stuck = False
    yield None


# Function passed to the pause_on_danger handler of the bot
def pause_on_danger_fn():
    '''Detects if there is viable loot in the vicinity.'''
    global item_id_blacklist
    global is_movement_stuck

    if is_movement_stuck:
        return True

    build = bot.config.build_handler
    if isinstance(build, DervSpiderFarmer) and build.status not in [DervBuildFarmStatus.Kill, DervBuildFarmStatus.Loot, DervBuildFarmStatus.Move, DervBuildFarmStatus.Wait]:
        return False

    valuable_loot_array = get_valid_loot_array()
    if not valuable_loot_array or len(valuable_loot_array) == 0:
        return False

    filtered_agent_ids = [agent_id for agent_id in valuable_loot_array if agent_id not in set(item_id_blacklist)]
    if not filtered_agent_ids or len(filtered_agent_ids) == 0:
        return False

    return True


# Coroutine function to handle farming
def execute_farm_routine(bot):
    global is_looting
    global is_farming

    if is_farming:
        return

    # Auto detect if enemies in the area
    enemy_array = get_enemy_array(custom_range=Range.Earshot.value, detectable_collection=FOES_MODEL_IDS)
    if not len(enemy_array):
        ConsoleLog(SCRIPT_NAME, 'No enemies detected')
        return

    ConsoleLog(SCRIPT_NAME, 'Entering kill routine...')
    is_farming = True
    # bot.config.build_handler.status = DervBuildFarmStatus.Kill

    timeout_timer = ThrottledTimer(30000) # 30sec
    timeout_timer.Start()

    single_remaining_mob_timer = ThrottledTimer(15000) # Try to kill last remaining mob for 15sec
    single_remaining_mob_timer.Stop()

    player_id = GLOBAL_CACHE.Player.GetAgentID()

    while True:
        enemy_array = get_enemy_array(custom_range=Range.Earshot.value, detectable_collection=FOES_MODEL_IDS)
        if len(enemy_array) == 0:
            bot.config.build_handler.status = DervBuildFarmStatus.Move
            yield None
            break  # all fog_nightmares dead

        if len(enemy_array) == 1:
            if single_remaining_mob_timer.IsStopped():
                single_remaining_mob_timer.Start()

            elif single_remaining_mob_timer.IsExpired():
                ConsoleLog(SCRIPT_NAME, 'Single remaining mob timeout, setting back to [Move] status')
                bot.config.build_handler.status = DervBuildFarmStatus.Move
                yield None
                break


        # Timeout check
        if timeout_timer.IsExpired():
            ConsoleLog(SCRIPT_NAME, 'Fight took too long, setting back to [Move] status')
            bot.config.build_handler.status = DervBuildFarmStatus.Move
            yield None
            break

        # Death check
        if Agent.IsDead(player_id):
            # handle death here
            ConsoleLog(SCRIPT_NAME, 'Died fighting, resetting farm')
            bot.config.build_handler.status = DervBuildFarmStatus.Setup
            yield from Routines.Yield.wait(1000)
            yield from Routines.Yield.Player.Resign()
            break

        yield from Routines.Yield.wait(100)

    ConsoleLog(SCRIPT_NAME, 'Finished farming.')
    is_farming = False

    yield from Routines.Yield.wait(100)

def EquipSkillBar(bot: Botting):
    yield from bot.config.build_handler.LoadSkillBar()


# Coroutine function to handle looting
def handle_loot(bot: Botting):
    global is_looting
    while True:
        # Wait until map is valid
        if not Routines.Checks.Map.MapValid() and not Routines.Checks.Map.IsExplorable():
            yield from Routines.Yield.wait(1000)
            continue

        if Agent.IsDead(GLOBAL_CACHE.Player.GetAgentID()):
            yield from Routines.Yield.wait(1000)
            continue

        if (
            Map.GetMapID() == MAGUS_STONE and
            isinstance(bot.config.build_handler, DervSpiderFarmer) and
            bot.config.build_handler.status in [DervBuildFarmStatus.Move, DervBuildFarmStatus.Wait]
        ):
            # Get the loot specified in the loot util file, continue with looting if any found
            valid_loot_array = get_valid_loot_array()
            if valid_loot_array and not is_looting:
                is_looting = True
                bot.config.build_handler.SetStatus(DervBuildFarmStatus.Loot)
                yield from loot_items(valid_loot_array)
                bot.config.build_handler.SetStatus(DervBuildFarmStatus.Move)
                # log from the last epicenter of the begining of the farm
                is_looting = False

        # Throttle the loop
        yield from Routines.Yield.wait(500)


# Loot function which loots items and handles blacklist for wanted items unable to loot
def loot_items(loot_array: list[int]):
    global item_id_blacklist

    yield from Routines.Yield.wait(1000)  # Wait for a moment before starting to loot
    ConsoleLog(SCRIPT_NAME, 'Looting items...')

    failed_items_id = yield from Routines.Yield.Items.LootItemsWithMaxAttempts(loot_array, log=True)
    if failed_items_id:
        ConsoleLog(SCRIPT_NAME, f'Failed to loot item with ID: {failed_items_id}, adding to blacklist')

        item_id_blacklist = item_id_blacklist + failed_items_id
        ConsoleLog(SCRIPT_NAME, f'Current blacklist: {item_id_blacklist}')

    ConsoleLog(SCRIPT_NAME, 'Looting items finished')
    yield from Routines.Yield.wait(1000)  # Wait for a moment after finishing looting


def wait_for_loot_to_finish():
    global is_looting
    while is_looting:
        yield from Routines.Yield.wait(500)






# ==================== HELPER METHODS ==================== #


#region helper methods
def get_enemy_array(custom_range = Range.Area.value * 1.50, detectable_collection: Iterable[int] = []) -> list[int]:
    px, py = GLOBAL_CACHE.Player.GetXY()
    enemy_array = Routines.Agents.GetFilteredEnemyArray(px, py, custom_range)
    return [
        agent_id
        for agent_id in enemy_array
        if Agent.GetModelID(agent_id) in detectable_collection
    ]



def set_bot_status(bot: Botting, status: str):
    '''Sets the bot's build status to the specified status.'''

    build = bot.config.build_handler
    if build is not None and isinstance(build, DervSpiderFarmer):
        yield from build.SetStatus(status)


# Reset the blacklisted loot item ids
def reset_item_blacklist():
    global item_id_blacklist
    item_id_blacklist = []
    yield None


# Single use alcohol function
def use_alcohol():
    alcohol_models = [
        (m.value if hasattr(m, "value") else int(m))
        for m in Routines.Yield.Upkeepers.ALCOHOL_ITEMS
    ]

    # Look for first available alcohol item
    item_id = 0
    for model_id in alcohol_models:
        item_id = GLOBAL_CACHE.Inventory.GetFirstModelID(model_id)
        if item_id:
            break
        
    if item_id:
        # nothing to use right now
        GLOBAL_CACHE.Inventory.UseItem(item_id)
        
    yield from Routines.Yield.wait(500)
    # yield from Routines.Yield.Items.UseItem(ModelID.Vial_Of_Absinthe.value)










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

path_1 = [
    #normal running routine
    (17561.23, 7616.28, DervBuildFarmStatus.Move, 0), # Before first spider group
    (19078.75, 4208.01, DervBuildFarmStatus.Move, 0), # After first spider group

    #balling running routine
    (19004.04, 3309.77, DervBuildFarmStatus.Ball, 0), # First back n forth to ball spider group 1
    (18504.34, 3394.30, DervBuildFarmStatus.Ball, 0),
    (19004.04, 3309.77, DervBuildFarmStatus.Ball, 0), # Second back n forth to ball spider group 2
    (18504.34, 3394.30, DervBuildFarmStatus.Kill, 0),


    # (18470.39, 3916.44, DervBuildFarmStatus.Kill), # Backup
    #kill spiders
    #loot
]

path_2  = [
    # From previous kill spot to narrow path
    (18768.15, 2279.14, DervBuildFarmStatus.Move, 0), # After killing first group to before narrow path
    (18254.00, 2098.56, DervBuildFarmStatus.Move, 0), # Zig zag to avoid block
    # (17911.47, 1191.82, DervBuildFarmStatus.Move, 0), # After zigzag to before narrow path

    # Insert back and forth to clear the narrow path
    (17580.91, 844.03, DervBuildFarmStatus.Move, 1000), # Start of narrow path, wait
    (17826.58, 1412.65, DervBuildFarmStatus.Move, 1000), # Move a bit back from the narrow path, wait (further)
    # (17655.59, 1163.28, DervBuildFarmStatus.Move, 1000), # Move a bit back from the narrow path, wait (closer)
    # (17952.61, 1345.80, DervBuildFarmStatus.Move, 1000), # Move a bit back from the narrow path, wait

    
    # Try to zigzag the narrow path
    (17750.43, 367.06, DervBuildFarmStatus.Move, 0), # Hug left side of narrow path
    (17418.65, 152.65, DervBuildFarmStatus.Move, 0), # Hug right side of narrow path

    # previous path
    # (17665.95, 185.75, DervBuildFarmStatus.Move, 0), # Hug left side of narrow path
    # (17381.34, -149.69, DervBuildFarmStatus.Move, 0), # Hug middle side of narrow path
    # (17560.50, -342.79, DervBuildFarmStatus.Move, 0), # More left side of narrow path
    # (17279.21, -687.44, DervBuildFarmStatus.Ball, 0), # After narrow path


    (17582.81, -3894.67, DervBuildFarmStatus.Ball, 1500), # First back n forth to ball spider group 2
    (16551.12, -2022.32, DervBuildFarmStatus.Kill, 350), # Last stop before killing routine (new)
    # (17221.04, -3275.86, DervBuildFarmStatus.Ball, 0), # 
    # (16925.17, -2726.17, DervBuildFarmStatus.Ball, 0),
    # (17582.81, -3894.67, DervBuildFarmStatus.Ball, 0), # Second back n forth to ball spider group 2
    # (16925.17, -2726.17, DervBuildFarmStatus.Kill, 1500), # Last stop before killing routine (before)
    # (16077.05, -1530.15, DervBuildFarmStatus.Kill, 1500), # First back n forth to ball spider group 2 (very far end stop)

    #kill spiders
    #loot


    # (17308.99, -2487.48, DervBuildFarmStatus.Ball), # First back n forth to ball spider group 2
    # (16785.13, -2110.67, DervBuildFarmStatus.Ball),
    # (17308.99, -2487.48, DervBuildFarmStatus.Ball), # Second back n forth to ball spider group 2
    # (16785.13, -2110.67, DervBuildFarmStatus.Kill),

]