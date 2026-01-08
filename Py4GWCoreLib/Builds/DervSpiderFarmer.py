import math
import random

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
from Py4GWCoreLib import Agent
from Py4GWCoreLib.Builds.AutoCombat import AutoCombat
from Py4GWCoreLib.Builds.BuildHelpers import BuildDangerHelper


# =================== BUILD ========================
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
            name="Derv Spider Farmer",
            required_primary=Profession.Dervish,
            required_secondary=Profession.Monk,
            template_code='OgOjkOrMLTmXfbcX0XyDqisX0kA',
            skills=[
                GLOBAL_CACHE.Skill.GetID("Sand_Shards"),
                GLOBAL_CACHE.Skill.GetID("Vow_of_Strength"),
                GLOBAL_CACHE.Skill.GetID("Mirage_Cloak"),
                GLOBAL_CACHE.Skill.GetID("Holy_Veil"),
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
        self.holy_veil = self.skills[3]
        self.balthazars_spirit = self.skills[4]
        self.drunken_master = self.skills[5]
        self.mystic_regen = self.skills[6]
        self.i_am_unstoppable = self.skills[7]

        # Build Status
        self.status = DervBuildFarmStatus.Setup
        self.spiked = False
        self.spiking = False

    def swap_to_scythe(self):
        if Agent.GetWeaponType(Player.GetAgentID())[0] != Weapon.Scythe:
            Keystroke.PressAndRelease(Key.F1.value)
            yield

    def swap_to_shield_set(self):
        if Agent.GetWeaponType(Player.GetAgentID())[0] == Weapon.Scythe:
            Keystroke.PressAndRelease(Key.F2.value)
            yield from Routines.Yield.wait(750)

    def is_target_correct_model_id(self, agent_id, model_id):
        if not agent_id:
            return False

        if Agent.GetModelID(agent_id) == model_id:
            return True
        return False

    def get_fog_nightmare_or_aloe_target(self, agent_ids):
        aloe_target = None
        fog_nightmare_target = None
        fog_nightmare_count = 0
        for agent_id in agent_ids:
            if self.is_target_correct_model_id(agent_id, AgentModelID.SPINED_ALOE):
                aloe_target = agent_id

        for agent_id in agent_ids:
            if self.is_target_correct_model_id(agent_id, AgentModelID.FOG_NIGHTMARE):
                fog_nightmare_count += 1
                fog_nightmare_target = agent_id

        if aloe_target and fog_nightmare_target and fog_nightmare_count > 1:
            return Routines.Agents.GetNearestEnemy(Range.Earshot.value)
        if aloe_target and fog_nightmare_count and fog_nightmare_count <= 1:
            return aloe_target
        if aloe_target:
            return aloe_target or fog_nightmare_target
        if fog_nightmare_target:
            return Routines.Agents.GetNearestEnemy(Range.Earshot.value)


    # Watches dangerous conditions and applies defensive skills as needed
    def _DefensiveWatcher(self):
        player_agent_id = GLOBAL_CACHE.Player.GetAgentID()
        is_iau_ready = Routines.Checks.Skills.IsSkillIDReady(self.i_am_unstoppable)

        player_agent_id = GLOBAL_CACHE.Player.GetAgentID()
        (px, py) = GLOBAL_CACHE.Player.GetXY()

        if Agent.IsCrippled(player_agent_id) or self.build_danger_helper.check_cripple_kd(px, py):
            has_iau = Routines.Checks.Effects.HasBuff(player_agent_id, self.i_am_unstoppable)
            has_mirage_cloak = Routines.Checks.Effects.HasBuff(player_agent_id, self.mirage_cloak)
            is_iau_ready = Routines.Checks.Skills.IsSkillIDReady(self.i_am_unstoppable)
            is_mirage_cloak_ready = Routines.Checks.Skills.IsSkillIDReady(self.mirage_cloak)

            if is_iau_ready and not has_iau:
                yield from Routines.Yield.Skills.CastSkillID(self.i_am_unstoppable, aftercast_delay=200)

            if is_mirage_cloak_ready and not has_mirage_cloak:
                yield from Routines.Yield.Skills.CastSkillID(self.mirage_cloak, aftercast_delay=200)

    
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
            if self.status == DervBuildFarmStatus.Setup:
                self.spiked = False

                # Checks for defensive buffs
                has_balth_spirit = Routines.Checks.Effects.HasBuff(GLOBAL_CACHE.Player.GetAgentID(), self.balthazars_spirit)
                has_holy_veil = Routines.Checks.Effects.HasBuff(GLOBAL_CACHE.Player.GetAgentID(), self.holy_veil)
                is_balth_spirit_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.balthazars_spirit)
                is_holy_veil_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.holy_veil)

                # Apply defensive buffs if not already present
                if is_balth_spirit_usable and not has_balth_spirit:
                    yield from Routines.Yield.Skills.CastSkillID(self.balthazars_spirit, aftercast_delay=1250)
            
                if is_holy_veil_usable and not has_holy_veil:
                    yield from Routines.Yield.Skills.CastSkillID(self.holy_veil, aftercast_delay=750)
            

            # General buff application during Move, Ball, and Kill statuses
            if self.status in [DervBuildFarmStatus.Move, DervBuildFarmStatus.Ball, DervBuildFarmStatus.Kill]:
                has_drunken_master = Routines.Checks.Effects.HasBuff(GLOBAL_CACHE.Player.GetAgentID(), self.drunken_master)

                is_drunken_master_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.drunken_master)

                # Drunken Master buff application
                if is_drunken_master_usable and not has_drunken_master:
                    yield from Routines.Yield.Skills.CastSkillID(self.drunken_master, aftercast_delay=250)

            # Defensive watcher only during move and kill phases
            if self.status in [DervBuildFarmStatus.Move, DervBuildFarmStatus.Kill]:
                has_mirage_cloak = Routines.Checks.Effects.HasBuff(GLOBAL_CACHE.Player.GetAgentID(), self.mirage_cloak)
                has_mystic_regen = Routines.Checks.Effects.HasBuff(GLOBAL_CACHE.Player.GetAgentID(), self.mystic_regen)
                is_mirage_cloak_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.mirage_cloak)
                is_mystic_regen_usable = yield from Routines.Yield.Skills.IsSkillIDUsable(self.mystic_regen)

                if is_mystic_regen_usable and not has_mystic_regen:
                    yield from Routines.Yield.Skills.CastSkillID(self.mystic_regen, aftercast_delay=1250)
                


            # Skills usable in all phases but dependent on nearby enemies
            yield from self._DefensiveWatcher()

        # player_agent_id = GLOBAL_CACHE.Player.GetAgentID()
        # has_dwarven_stability = Routines.Checks.Effects.HasBuff(player_agent_id, self.dwarven_stability)
        # has_mystic_regen = Routines.Checks.Effects.HasBuff(player_agent_id, self.mystic_regen)
        # has_mystic_vigor = Routines.Checks.Effects.HasBuff(player_agent_id, self.mystic_vigor)
        # player_hp = Agent.GetHealth(GLOBAL_CACHE.Player.GetAgentID())

        # if (
        #     (yield from Routines.Yield.Skills.IsSkillIDUsable(self.mystic_vigor))
        #     and not has_mystic_vigor
        #     and player_hp < 0.80
        #     and not self.status == DervBuildFarmStatus.Setup
        # ):
        #     yield from Routines.Yield.Skills.CastSkillID(self.mystic_vigor, aftercast_delay=750)
        #     return

        # if (
        #     (yield from Routines.Yield.Skills.IsSkillIDUsable(self.dwarven_stability))
        #     and not has_dwarven_stability
        #     and not self.status == DervBuildFarmStatus.Setup
        # ):
        #     yield from Routines.Yield.Skills.CastSkillID(self.dwarven_stability, aftercast_delay=250)
        #     return

        # if (
        #     (yield from Routines.Yield.Skills.IsSkillIDUsable(self.mystic_regen))
        #     and not has_mystic_regen
        #     and player_hp < 0.95
        # ):
        #     yield from Routines.Yield.Skills.CastSkillID(self.mystic_regen, aftercast_delay=750)
        #     return

        # if self.status == DervBuildFarmStatus.Move:
        #     yield from self.swap_to_shield_set()
        #     self.spiked = False
        #     if (
        #         (yield from Routines.Yield.Skills.IsSkillIDUsable(self.dash))
        #         and has_dwarven_stability
        #         and Agent.IsMoving(GLOBAL_CACHE.Player.GetAgentID())
        #     ):
        #         yield from Routines.Yield.Skills.CastSkillID(self.dash, aftercast_delay=100)
        #         return

        # if self.status == DervBuildFarmStatus.Ball:
        #     yield from self.swap_to_shield_set()
        #     self.spiked = False

        # if self.status == DervBuildFarmStatus.Kill:
        #     player_pos = GLOBAL_CACHE.Player.GetXY()
        #     player_current_energy = Agent.GetEnergy(player_agent_id) * Agent.GetMaxEnergy(
        #         player_agent_id
        #     )
        #     remaining_enemies = Routines.Agents.GetFilteredEnemyArray(player_pos[0], player_pos[1], Range.Earshot.value)
        #     next_target = self.get_fog_nightmare_or_aloe_target(remaining_enemies)

        #     if next_target:
        #         yield from self.swap_to_scythe()
        #         if self.is_target_correct_model_id(next_target, AgentModelID.SPINED_ALOE):
        #             agent_x, agent_y = Agent.GetXY(next_target)
        #             player_x, player_y = GLOBAL_CACHE.Player.GetXY()

        #             # === Step 1: Calculate vector from player -> target ===
        #             dx = agent_x - player_x
        #             dy = agent_y - player_y
        #             dist = math.hypot(dx, dy)

        #             if dist > Range.Adjacent.value:
        #                 # === Step 2: Normalize direction vector ===
        #                 nx, ny = dx / dist, dy / dist

        #                 # === Step 3: Pick sidestep direction (left or right) ===
        #                 sidestep_dir = random.choice([-1, 1])  # -1 = left, +1 = right
        #                 sidestep_distance = random.randint(200, 400)  # adjust to how big sidestep should be

        #                 # perpendicular vector for sidestep
        #                 sx, sy = -ny * sidestep_dir, nx * sidestep_dir

        #                 sidestep_x = player_x + sx * sidestep_distance
        #                 sidestep_y = player_y + sy * sidestep_distance

        #                 # === Step 4: Move to sidestep position first ===
        #                 GLOBAL_CACHE.Player.Move(sidestep_x, sidestep_y)
        #                 yield from Routines.Yield.wait(1000)  # small wait

        #                 # === Step 5: Move to a point within Adjacent range of target ===
        #                 stop_distance = Range.Adjacent.value
        #                 final_x = agent_x - nx * stop_distance
        #                 final_y = agent_y - ny * stop_distance

        #                 GLOBAL_CACHE.Player.Move(final_x, final_y)
        #                 yield from Routines.Yield.wait(2000)  # allow move to finish

        #         yield from Routines.Yield.Agents.InteractAgent(next_target)
        #         has_vow_of_strength = Routines.Checks.Effects.HasBuff(player_agent_id, self.vow_of_strength)
        #         has_grenths_aura = Routines.Checks.Effects.HasBuff(player_agent_id, self.grenths_aura)
        #         if (
        #             (yield from Routines.Yield.Skills.IsSkillIDUsable(self.grenths_aura))
        #             and len(remaining_enemies) >= 2
        #             and not has_grenths_aura
        #         ) or player_hp < 0.50:
        #             yield from Routines.Yield.Skills.CastSkillID(self.grenths_aura, aftercast_delay=250)
        #             return

        #         if (yield from Routines.Yield.Skills.IsSkillIDUsable(self.vow_of_strength)) and not has_vow_of_strength:
        #             yield from Routines.Yield.Skills.CastSkillID(self.vow_of_strength, aftercast_delay=250)
        #             return
        #         has_vow_of_strength = Routines.Checks.Effects.HasBuff(player_agent_id, self.vow_of_strength)

        #         if (
        #             (
        #                 yield from Routines.Yield.Skills.IsSkillIDUsable(self.staggering_force)
        #                 and Routines.Yield.Skills.IsSkillIDUsable(self.eremites_attack)
        #             )
        #             and has_vow_of_strength
        #             and has_grenths_aura
        #             and player_current_energy >= 12
        #             and len(remaining_enemies) >= 2
        #         ):
        #             yield from Routines.Yield.Agents.TargetNearestEnemy(Range.Earshot.value)
        #             yield from Routines.Yield.Skills.CastSkillID(self.staggering_force, aftercast_delay=250)
        #             has_staggering_force = Routines.Checks.Effects.HasBuff(player_agent_id, self.staggering_force)
        #             if has_staggering_force and player_current_energy >= 10:
        #                 yield from Routines.Yield.Skills.CastSkillID(self.eremites_attack, aftercast_delay=250)
        #                 return
        #         yield
        #         return
        # yield
        # return


# =================== BUILD END ========================
