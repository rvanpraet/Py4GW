from PyItem import Rarity
from Bots.marks_coding_corner.utils.loot_utils import is_valid_item
from Py4GWCoreLib import Agent, AgentArray, Item
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.enums_src.GameData_enums import Range
from Py4GWCoreLib.enums_src.Model_enums import ModelID


VIABLE_LOOT = {
    # Coin
    ModelID.Gold_Coins,
    # Lockpick
    ModelID.Lockpick,
}

def get_valid_loot_array(viable_loot=VIABLE_LOOT, loot_salvagables=False):
    def filter_fn(agent_id: int) -> bool:
        '''
        Filter function to determine if an item agent is valuable based on model ID and other criteria.
        '''

        # Get item ID and model ID
        item_id = Agent.GetItemAgentItemID(agent_id)
        model_id = Item.GetModelID(item_id)

        # Check if item is valuable according to specific filter
        is_valuable_item = filter_valuable_weapon_type(item_id) or model_id in viable_loot
        is_valuable_dye = model_id == ModelID.Vial_Of_Dye and (GLOBAL_CACHE.Item.GetDyeColor(item_id) == 10 or GLOBAL_CACHE.Item.GetDyeColor(item_id) == 12)

        return (is_valuable_item or is_valuable_dye) and is_valid_item(agent_id)

    # Create the lootarray filtered by distance
    loot_array = AgentArray.GetItemArray()
    loot_array: list[int] = AgentArray.Filter.ByDistance(loot_array, GLOBAL_CACHE.Player.GetXY(), Range.Spellcast.value * 3.00)
    

    # Create agent array filtered by viability
    agent_array = AgentArray.GetItemArray()
    item_array_model: list[int] = AgentArray.Filter.ByCondition(agent_array, filter_fn)


    # Handle salvagable items if needed
    item_array_salv = []
    if loot_salvagables:
        item_array_salv = AgentArray.Filter.ByCondition(
            agent_array, lambda agent_id: Item.Usage.IsSalvageable(Agent.GetItemAgentItemID(agent_id))
        )
    
    # Make unique and sort
    item_array = list(set(item_array_model + item_array_salv))
    item_array: list[int] = AgentArray.Sort.ByDistance(item_array, GLOBAL_CACHE.Player.GetXY())

    return item_array



def filter_valuable_weapon_type(item_id: int) -> bool:
    '''
    Checks for extreme rare stats on shields, swords and offhands

    q5 shields with ideal armor or q8 with max armor

    q8 swords with max damage

    q8 offhands with max energy (gold rarity only)
    '''
    desired_skins = [2236, 2237, 1052]
    desired_types = [12, 24, 27] # Offhand, Shield, Sword
    item_instance = Item.item_instance(item_id)
    item_modifiers = item_instance.modifiers
    item_req = 13 # Default high req to skip uninteresting items

    # immediate accept for desired skins
    if item_instance.model_id in desired_skins:
        return True

    # Filter out white items and undesired types early
    if item_instance.rarity == Rarity.White or item_instance.item_type.ToInt() not in desired_types:
        return False

    # Check Q9 max stats
    for mod in item_modifiers:
        # Dont waste time on uninteresting mods
        # [requirement, shield armor, sword damage, offhand energy]
        if mod.GetIdentifier() not in [10136, 42936, 42920, 26568]:
            continue

        # Store item requirement
        if mod.GetIdentifier() == 10136:
            item_req = mod.GetArg2() # Item requirement value

            # high req found, break early
            if item_req >= 9:
                break
        
        # Handle Shield
        # 42936 = Shield armor mod identifier
        if item_instance.item_type.ToInt() == 24 and mod.GetIdentifier() == 42936:
            has_ideal_q4_stats = mod.GetArg1() == 12 # Ideal shield armor for q5
            has_ideal_q5_stats = mod.GetArg1() == 13 # Ideal shield armor for q5
            has_ideal_q6_stats = mod.GetArg1() == 14
            has_ideal_q7_stats = mod.GetArg1() == 15
            has_max_stats = mod.GetArg1() == 16 # Max armor

            return (
                (item_req == 4 and has_ideal_q4_stats)
                or (item_req == 5 and has_ideal_q5_stats)
                or (item_req == 6 and has_ideal_q6_stats)
                or (item_req == 7 and has_ideal_q7_stats)
                or has_max_stats
            )

        # Handle Sword -- Only Q8 with max stats are interesting
        # 42920 = Sword damage mod identifier
        if item_instance.item_type.ToInt() == 27 and mod.GetIdentifier() == 42920:
            has_max_stats = mod.GetArg2() == 15 and mod.GetArg1() == 22 # Max damage mod
            return has_max_stats
        

        # Handle Offhand -- Only Q8 Offhands with max stats are interesting
        # 26568 = Offhand energy mod identifier
        if item_instance.item_type.ToInt() == 12 and mod.GetIdentifier() == 26568:
            has_max_stats = mod.GetArg1() == 12 # Max Energy mod
            is_rarity_gold = item_instance.is_rarity_gold # Only interested in gold offhands
            return has_max_stats and is_rarity_gold

    return False