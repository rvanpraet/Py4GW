import math
import random

import Py4GW

from Py4GWCoreLib import GLOBAL_CACHE
from Py4GWCoreLib import ActionQueueManager
from Py4GWCoreLib import AgentModelID
from Py4GWCoreLib import BuildMgr
from Py4GWCoreLib import Key
from Py4GWCoreLib import Keystroke
from Py4GWCoreLib import Player
from Py4GWCoreLib import Profession
from Py4GWCoreLib import Range
from Py4GWCoreLib import Routines
from Py4GWCoreLib import Weapon
from Py4GWCoreLib import Agent, AgentArray
from Py4GWCoreLib.Builds.AutoCombat import AutoCombat
from Py4GWCoreLib.Builds.BuildHelpers import BuildDangerHelper
from Py4GWCoreLib.py4gwcorelib_src.Console import ConsoleLog


# =================== BUILD ========================
BUILD_NAME = "Derv Spider Farmer"
class DervBuildFarmStatus:
    Setup = 'setup'
    Move = 'move'
    Ball = 'ball'
    Kill = 'kill'
    Loot = 'loot'
    Wait = 'wait'


class DervSpiderFarmer(BuildMgr):
    def __init__(self, build_danger_helper: BuildDangerHelper = BuildDangerHelper()):
        super().__init__(
            name=BUILD_NAME,
            required_primary=Profession.Dervish,
            required_secondary=Profession.Monk,
            template_code='OgOjkOrMLTmXfbcXebyDqisX0kA',
            skills=[
                GLOBAL_CACHE.Skill.GetID("Sand_Shards"),
                GLOBAL_CACHE.Skill.GetID("Vow_of_Strength"),
                GLOBAL_CACHE.Skill.GetID("Mirage_Cloak"),
                GLOBAL_CACHE.Skill.GetID("Harriers_Grasp"),
                GLOBAL_CACHE.Skill.GetID("Balthazars_Spirit"),
                GLOBAL_CACHE.Skill.GetID("Drunken_Master"),
                GLOBAL_CACHE.Skill.GetID("Mystic_Regeneration"),
                GLOBAL_CACHE.Skill.GetID("I_Am_Unstoppable"),
            ],
        )

        # Build handlers
        self.build_danger_helper = build_danger_helper
        self.auto_combat_handler: BuildMgr = AutoCombat()

        # Build skills
        self.sand_shards = self.skills[0]
        self.vow_of_strength = self.skills[1]
        self.mirage_cloak = self.skills[2]
        self.harriers_grasp = self.skills[3]
        self.balthazars_spirit = self.skills[4]
        self.drunken_master = self.skills[5]
        self.mystic_regen = self.skills[6]
        self.i_am_unstoppable = self.skills[7]

        # Build Status
        self.status = DervBuildFarmStatus.Setup

    def SetStatus(self, new_status: str):
        if new_status not in [
            DervBuildFarmStatus.Setup,
            DervBuildFarmStatus.Move,
            DervBuildFarmStatus.Ball,
            DervBuildFarmStatus.Kill,
            DervBuildFarmStatus.Loot,
            DervBuildFarmStatus.Wait
        ]:  
            raise ValueError(f"Invalid status: {new_status}")
        
        ConsoleLog(BUILD_NAME, f"Setting bot status to: {new_status}", Py4GW.Console.MessageType.Info)
        self.status = new_status
        if new_status == DervBuildFarmStatus.Kill:
            yield from self._swap_to_scythe()

        else:
            yield from self._swap_to_shield_set()

    # Helper functions            
    def _swap_to_scythe(self):
        if Agent.GetWeaponType(Player.GetAgentID())[0] != Weapon.Scythe:
            Keystroke.PressAndRelease(Key.F1.value)
            yield from Routines.Yield.wait(250)


    def _swap_to_shield_set(self):
        if Agent.GetWeaponType(Player.GetAgentID())[0] == Weapon.Scythe:
            Keystroke.PressAndRelease(Key.F2.value)
            yield from Routines.Yield.wait(250)


    def _is_target_correct_model_id(self, agent_id, model_id):
        if not agent_id:
            return False

        if Agent.GetModelID(agent_id) == model_id:
            return True
        return False


    def _get_next_target(self):
        player_pos = GLOBAL_CACHE.Player.GetXY()
        agent_ids = Routines.Agents.GetFilteredEnemyArray(player_pos[0], player_pos[1], Range.Earshot.value)
        target_arr = [target_id for target_id in agent_ids if self._is_target_correct_model_id(target_id, AgentModelID.SPIDER)]
        target_arr = AgentArray.Sort.ByDistance(target_arr, player_pos) 

        return target_arr[1] if len(target_arr) > 1 else target_arr[0] if target_arr else 0


    def _SetupWatcher(self):
        if self.status != DervBuildFarmStatus.Setup:
            yield None
            return


        # Checks for defensive buffs
        has_balth_spirit = Routines.Checks.Effects.HasBuff(GLOBAL_CACHE.Player.GetAgentID(), self.balthazars_spirit)
        is_balth_spirit_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.balthazars_spirit)

        # Apply defensive buffs if not already present
        if is_balth_spirit_usable and not has_balth_spirit:
            yield from Routines.Yield.Skills.CastSkillID(self.balthazars_spirit, aftercast_delay=1250)

    # Watcher routines
    # Watches dangerous conditions and applies defensive skills as needed
    def _DefensiveWatcher(self):
        player_agent_id = GLOBAL_CACHE.Player.GetAgentID()
        (px, py) = GLOBAL_CACHE.Player.GetXY()

        has_iau = Routines.Checks.Effects.HasBuff(player_agent_id, self.i_am_unstoppable)
        has_mirage_cloak = Routines.Checks.Effects.HasBuff(player_agent_id, self.mirage_cloak)
        is_iau_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.i_am_unstoppable)
        is_mirage_cloak_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.mirage_cloak)

        # Mystic regen only during move and kill phases
        if self.status in [DervBuildFarmStatus.Move, DervBuildFarmStatus.Kill]:
            has_mystic_regen = Routines.Checks.Effects.HasBuff(GLOBAL_CACHE.Player.GetAgentID(), self.mystic_regen)
            is_mystic_regen_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.mystic_regen)

            if is_mystic_regen_usable and not has_mystic_regen:
                yield from Routines.Yield.Skills.CastSkillID(self.mystic_regen, aftercast_delay=1250)


        # Low health mirage cloak in case enemies are too far to detect with danger detector
        if Agent.GetHealth(player_agent_id) <= 0.99 and is_mirage_cloak_usable:
            yield from Routines.Yield.Skills.CastSkillID(self.mirage_cloak, aftercast_delay=200)


        # Cripple danger handling
        if Agent.IsCrippled(player_agent_id) or self.build_danger_helper.check_cripple_kd(px, py):
            if is_iau_usable and not has_iau:
                yield from Routines.Yield.Skills.CastSkillID(self.i_am_unstoppable, aftercast_delay=200)

            if is_mirage_cloak_usable and not has_mirage_cloak:
                yield from Routines.Yield.Skills.CastSkillID(self.mirage_cloak, aftercast_delay=200)

        yield None


        # Anti cripple when IAU is down
        if Agent.IsCrippled(player_agent_id) and not has_iau and not is_iau_usable and self.status != DervBuildFarmStatus.Kill:
            has_harriers_grasp = Routines.Checks.Effects.HasBuff(player_agent_id, self.harriers_grasp)
            is_harriers_grasp_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.harriers_grasp)

            if is_harriers_grasp_usable and not has_harriers_grasp:
                yield from Routines.Yield.Skills.CastSkillID(self.harriers_grasp, aftercast_delay=200)

        yield None


    # While in kill mode, detect nearby enemies and spike
    def _OffensiveWatcher(self):
        if self.status != DervBuildFarmStatus.Kill:
            yield None
            return
    
        # Get the next target
        player_agent_id = GLOBAL_CACHE.Player.GetAgentID()
        next_target = self._get_next_target()

        # No target found, exit
        if not next_target:
            yield None
            return
        
        # Conditions to cast offensive buffs
        has_sand_shards = Routines.Checks.Effects.HasBuff(player_agent_id, self.sand_shards)
        has_vow_of_strength = Routines.Checks.Effects.HasBuff(player_agent_id, self.vow_of_strength)
        is_sand_shards_usable = Routines.Yield.Skills.IsSkillIDUsable(self.sand_shards)
        is_vow_of_strength_usable = Routines.Yield.Skills.IsSkillIDUsable(self.vow_of_strength)

        # Execute killing
        yield from Routines.Yield.Agents.InteractAgent(next_target)

        if is_sand_shards_usable and not has_sand_shards:
            yield from Routines.Yield.Skills.CastSkillID(self.sand_shards, aftercast_delay=1250)

        elif is_vow_of_strength_usable and not has_vow_of_strength:
            yield from Routines.Yield.Skills.CastSkillID(self.vow_of_strength, aftercast_delay=1250)

        yield None

    
    # Override this method from Botting class to handle skill casting
    def ProcessSkillCasting(self):
        while True:
            # Check basic conditions where skill handling should be skipped
            
            # Check if map has fully loaded
            if not Routines.Checks.Map.MapValid():
                yield from Routines.Yield.wait(1000)
                continue
            

            # Player is dead
            if Agent.IsDead(GLOBAL_CACHE.Player.GetAgentID()):
                yield from Routines.Yield.wait(1000)
                continue


            # Cannot cast skills right now, throttle 100ms
            if not Routines.Checks.Skills.CanCast():
                yield from Routines.Yield.wait(100)
                continue


            # Skip skill casting while looting or waiting
            if self.status == DervBuildFarmStatus.Loot or self.status == DervBuildFarmStatus.Wait:
                yield from Routines.Yield.wait(100)
                continue


            # Setup phase logic
            yield from self._SetupWatcher()
            
            # Skills usable in all phases but dependent on nearby enemies
            yield from self._DefensiveWatcher()

            # General buff application during Move, Ball, and Kill statuses
            if self.status in [DervBuildFarmStatus.Setup, DervBuildFarmStatus.Move, DervBuildFarmStatus.Ball, DervBuildFarmStatus.Kill]:
                has_drunken_master = Routines.Checks.Effects.HasBuff(GLOBAL_CACHE.Player.GetAgentID(), self.drunken_master)

                is_drunken_master_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.drunken_master)

                # Drunken Master buff application
                if is_drunken_master_usable and not has_drunken_master:
                    yield from Routines.Yield.Skills.CastSkillID(self.drunken_master, aftercast_delay=250)
                

            # Offensive watcher during kill phase spikes enemies
            yield from self._OffensiveWatcher()


            # Throttle loop
            yield from Routines.Yield.wait(100)
