import appdaemon.plugins.hass.hassapi as hass
import localutils.persistent_data
import json
import configparser
import os
from pprint import pprint


# supported_features consts
TARGET_TEMPERATURE = 1
TARGET_TEMPERATURE_RANGE = 2
TARGET_HUMIDITY = 4
FAN_MODE = 8
PRESET_MODE = 16
SWING_MODE = 32
AUX_HEAT = 64



SCRIPT_DIR = os.path.realpath(os.path.dirname(__file__))
with open(f"{SCRIPT_DIR}/config.json") as fh:
  CONF = json.load(fh)

class VirtualThermostat():
  def __init__(self, base_entity, uid, name, source_entity):
    self.uid = uid
    self.base = base_entity
    self.name = name
    self.source_entity = source_entity

    self.saved_attrs = [
      'fan_mode',
      'target_temp_high',
      'target_temp_low',
    ]  

    attrs = {
      "hvac_modes": "off, heat, cool, heat_cool, auto".split(", "),
      "fan_modes": "auto, on".split(", "),
      "hvac_action": "idle",
      "fan_mode": "auto",
      "temperature": 78,
      "target_temp_high": 80,
      "target_temp_low": 70,
      "min_temp": 60,
      "max_temp": 90,
      "target_temp_step": 1,
      "friendly_name": self.name,
      "supported_features": FAN_MODE | TARGET_TEMPERATURE_RANGE
    }

    saved_attr_data = self.base.persist.get(f"vtstat-{self.uid}")
    if saved_attr_data:
      saved_attr_data = json.loads(saved_attr_data)
      attrs.update({k: saved_attr_data[k] for k in saved_attr_data if k in self.saved_attrs})

    state_data = self.base.persist.get(f"vtstat-{self.uid}-state")
    if not state_data:
      state_data = 'heat_cool'
    else:
      state_data = state_data.decode('utf-8')

    self.set_state(state=state_data, attributes=attrs, replace=True)

    self.base.listen_state(self.update_temp, self.source_entity)
    self.update_temp(self.source_entity, None, None, self.base.get_state(self.source_entity), {})
    self.base.listen_state(self.state_change_events, f"climate.{self.uid}", attribute='all')
    self.base.listen_event(self.events, event="call_service", service="set_temperature", entity_id=f"climate.{self.uid}")
    self.base.listen_event(self.events, event="call_service", service="set_hvac_mode", entity_id=f"climate.{self.uid}")

  def set_state(self, **kwargs):
    self.base.set_state(f"climate.{self.uid}", **kwargs)

  def get_state(self, **kwargs):
    return self.base.get_state(f"climate.{self.uid}", **kwargs)

  def listen_state(self, callback, **kwargs):
    self.base.listen_state(callback, f"climate.{self.uid}", **kwargs)

  def update_temp(self, entity, attribute, old, new, kwargs):
    self.base.set_state(f"climate.{self.uid}", attributes={
      "current_temperature": float(new)
    })

  def get_hvac_action(self):
    return self.get_state(attribute='hvac_action')

  def state_change_events(self, entity, attribute, old, new, kwargs):
    #self.base.log(f"got state_change event: {entity}, {attribute}, new: {new}, {kwargs}")
    
    swing_range = 1.0

    if new['attributes']['hvac_action'] != 'heating' and new['attributes']['current_temperature'] < new['attributes']['target_temp_low'] - swing_range:
      #self.base.log("setting to heating mode")
      self.set_state(attributes={"hvac_action": "heating"})
    if new['attributes']['hvac_action'] != 'cooling' and new['attributes']['current_temperature'] > new['attributes']['target_temp_high'] + swing_range:
      #self.base.log("setting to heating mode")
      self.set_state(attributes={"hvac_action": "cooling"})
    if ( new['attributes']['hvac_action'] != 'idle' and 
         new['attributes']['current_temperature'] >= new['attributes']['target_temp_low'] + swing_range and 
         new['attributes']['current_temperature'] <= new['attributes']['target_temp_high'] - swing_range ):
      #self.base.log("setting to idle mode")
      self.set_state(attributes={"hvac_action": "idle"})

    #persist state
    data = {k: new['attributes'][k] for k in self.saved_attrs if k in new['attributes']}
    self.base.log(f"persisting data: {data}")
    self.base.persist.set(f"vtstat-{self.uid}", json.dumps({k: new['attributes'][k] for k in self.saved_attrs if k in new['attributes']}))
    self.base.persist.set(f"vtstat-{self.uid}-state", new['state'])
    
    
 

  def events(self, event_name, kwargs, *args):
    if kwargs['service_data']['entity_id'] != f"climate.{self.uid}":
      return

    if event_name == 'call_service':
      self.base.log(f"{self.uid}: got event: {event_name}, kwargs1: {kwargs}, {args}")

    if event_name == 'call_service' and kwargs['service'] == 'set_temperature':
      #self.base.log("got set temp...")
      self.set_state(attributes={k: kwargs['service_data'][k] for k in kwargs['service_data'] if k in ['target_temp_low', 'target_temp_high']})
    if event_name == 'call_service' and kwargs['service'] == 'set_hvac_mode':
      #self.base.log("got set temp...")
      self.set_state(state=kwargs['service_data']['hvac_mode'])
   


class VirtualHVAC():
  def  __init__(self, base_obj, watched_thermostats):
    self.base_obj = base_obj
    self.watched_thermostats = watched_thermostats

    for t in self.watched_thermostats:
      #self.base_obj.log(f"watching: {t}")
      t.listen_state(self.thermostat_event, attribute="hvac_action")

  #def check_calling_heat(self, params):
  #  swing_range = 1.0

  #  if params['current_temperature'] < params['target_temp_low'] - (-1*swing_range if params['hvac_action'] == 'heating' else swing_range):
  #    return True

  def thermostat_event(self, entity, attribute, old, new, kwargs):
    self.base_obj.log(f"got thermostat event: {entity}, {attribute}, {old}, {new}, {kwargs}")


    #self.base_obj.log(f"get hvac_actions: {[x.get_hvac_action() for x in self.watched_thermostats]}")
    if any([x.get_hvac_action() == 'heating' for x in self.watched_thermostats]):
      self.base_obj.log(" - ensuring heat is ON")
      self.heating_action(enable=True)
    elif any([x.get_hvac_action() == 'cooling' for x in self.watched_thermostats]):
      self.base_obj.log(" - ensuring cooling is ON")
      self.cooling_action(enable=True)
    else:
      self.base_obj.log(" - ensuring heat is OFF")
      self.heating_action(enable=False)
      self.cooling_action(enable=False)


class FurnaceHVAC(VirtualHVAC):
  def __init__(self, base_obj, base_thermostat_entity, *args, **kwargs):
    super().__init__(base_obj, *args, **kwargs)
    self.base_thermostat_entity = base_thermostat_entity

  def heating_action(self, enable=True):
    target_temp = -1
    current_temp = float(self.base_obj.get_state(self.base_thermostat_entity, attribute='current_temperature'))
    if enable:
      target_temp = current_temp + 2
    else:
      target_temp = current_temp - 2

    self.base_obj.log(f"setting new temp for {self.base_thermostat_entity} to: {target_temp}")
      #self.base_obj.call_service("climate/set_temperature", target=self.base_thermostat_entity, data={'temperature': current_temp + 2})

  def cooling_action(self, enable=True):
    fan_mode = 'auto'
    if enable:
      self.base_obj.log("turning hvac fan on")
      fan_mode = 'on'
    else:
      self.base_obj.log("turning hvac fan off")
      fan_mode = 'auto'
    self.base_obj.call_service("climate/set_fan_mode", entity_id=self.base_thermostat_entity, fan_mode=fan_mode)


class AllVirtualThermostats(hass.Hass):

  def initialize(self):
    self.log("Hello from AppDaemon")
    self.log("You are now ready to run Apps!")

    self.persist = localutils.persistent_data.PersistentData('all-virtual-thermostats', self)

    self.all_thermostats = {}
    for thermostat in CONF['thermostats']:
      self.all_thermostats[thermostat['uid']] = VirtualThermostat(self, **thermostat)

    self.all_vhvacs = []
    for hv in CONF['hvac_sources']:
      self.all_vhvacs.append(
        FurnaceHVAC(
          self, 
          hv['base_thermostat_entity'], 
          [ self.all_thermostats[x] for x in self.all_thermostats.keys() if x in hv['virtual_thermostat_ids'] ]
        )
      )
