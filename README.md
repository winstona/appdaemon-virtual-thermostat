 # Prereqs

 - appdaemon set up and configured with Home Assistant
 - redis (see docker-compose example below)
 
 
 # Installation

 ```
 cd <appdamon apps dir>
 git clone https://github.com/winstona/appdaemon-localutils localutils # if not already cloned
 git clone https://github.com/winstona/appdaemon-virtual-thermostat virtual-thermostat
 ```

 - create `config.json` in repo folder (see `config.json.example`)

 ## HA Dashboard Panel

 Example section to add all virtual thermostats in one pane is in `dashboard.yaml`. The virtual thermostats created are just standard climate thermostats and can be integrated in any dashboard per usual, so this step is optional.

 Requires:
 - easy-layout-card (https://github.com/kamtschatka/lovelace-easy-layout-card)
 - auto-entities (https://github.com/thomasloven/lovelace-auto-entities)
 - stack-in-card (https://github.com/custom-cards/stack-in-card)
 - apexcharts-card (https://github.com/RomRider/apexcharts-card)
 - better-thermostat-ui-card (https://github.com/KartoffelToby/better-thermostat-ui-card)

 ## config.json

 - **thermostats**<br>
   List of virtual thermostats to create
   - **uid** - required<br>
     unique identifier assigned to this virtual thermostats, used to reference this thermostat from other places in code/config
   - **name** - required<br>
     friendly name displayed in HA UI
   - **source_entity** - required<br>
     temperature entity used for this virtual thermostat
   - **class** - optional<br>
     override default thermostat with a custom thermostat for more complex configurations (see `custom_thermostats.py`)
   - **<other config>**<br>
     additional config values can be included and used in custom thermostats
 - **hvac_sources**<br>
   List of `climate` entities to control
   - **base_thermostat_entity** - required<br>
     entity to control (currently only supports `climate` entities)
   - **virtual_thermostat_ids** - required<br>
     list of thermostat `uid`'s above that affect this thermostat


## redis docker-compose

```
services:
  ...
  redis:
    image: redis
    ports:
      - "6379"
    volumes:
    - "<local disk>/data:/data"
```