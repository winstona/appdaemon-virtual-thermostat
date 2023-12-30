import virtual_thermostat


# only enable hvac action if min/max of differential_entities is greater than some threshold
class DifferentialThermostat(virtual_thermostat.VirtualThermostat):
  def __init__(self, base_entity, uid, name, source_entity, differential_entities):
    base_entity.log("init diff_thermostat")
    self.differential_entities = differential_entities
    super().__init__(base_entity, uid, name, source_entity)
    base_entity.log("init diff_thermostat2")

  def update_hvac_action(self, value):
    self.base.log("call update hvac+action from differentialthermostat")

    values = []
    for x in self.differential_entities:
      x = ({'entity_id': x} if isinstance(x, str) else x)
      self.base.log(f"looking up: {x}")
      values.append(float(self.base.get_state(**({k: v for k,v in x.items()}))))

    self.base.log(f" got values2: {values}: diff: {max(values)-min(values)}")

    if max(values)-min(values) > 5.0:
      return super().update_hvac_action(value)
    self.base.log("skipped update hvac option because diff wasnt large enough")


# create delayed stages (if thermostat is still in an hvac action) to step up heating
# needs if stage 1 can't keep up
class TwoStageThemostat(virtual_thermostat.VirtualThermostat):
  def __init__(self, base_entity, uid, name, source_entity):
    self.stage2_timer = None
    super().__init__(base_entity, uid, name, source_entity)

  def update_hvac_action(self, value):
    self.base.log("call update hvac+action from twostagethermostat")

    if value == 'heating':
      if value != self.get_hvac_action():
        self.base.log("setting up timer to trigger 2nd stage if needed")
        self.stage2_timer = self.base.run_in(self.stage2_handler, 15*60)
        self.set_state(attributes={"hvac_action_stage": '1'})

    else:
      if self.stage2_timer != None:
        self.base.log("cancelling timer")
        self.base.cancel_timer(self.stage2_timer)
        self.stage2_timer = None

    return super().update_hvac_action(value)
  
  def stage2_handler(self, *args, **kwargs):
    self.base.log("running stage2...")
    self.set_state(attributes={"hvac_action_stage": '2'})

