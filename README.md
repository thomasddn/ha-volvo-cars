# Volvo Cars Home Assistant integration

This integration provides access to your Volvo car, provided your model and region are supported by Volvo's public API. This is not a one-to-one replacement for the official Volvo app, as the app has access to more resources than those available through the public API.

Supported regions include: Europe, the Middle East, and Africa. For a complete list of supported countries, check out [Volvo's API documentation](https://developer.volvocars.com/terms-and-conditions/apis-supported-locations/). Even if you're not in one of the listed countries, you might still get lucky! You'll need to try it to find out.

Now check out the features section for details on what you'll get!

[![GitHub release][releases-shield]][releases]
[![Github downloads][downloads-shield]][releases]
[![CI main][ci-main-shield]][ci-workflow]
[![CI dev][ci-dev-shield]][ci-workflow]
[![HACS][hacs-shield]][hacs]
[![Sponsor][sponsor-shield]](#sponsor)

> [!IMPORTANT]
> Coming over from volvo2mqtt? Hi! 👋 Please [read this](https://github.com/thomasddn/ha-volvo-cars/wiki/volvo2mqtt).

## ✨ Features

### General

- Multiple cars
- Multiple accounts
- Multiple languages: Czech (cs), Dutch (nl), English (en), Finnish (fi), French (fr), German (de), Hungarian (hu), Norwegian Bokmål (nb), Polish (pl), Portuguese Brazil (pt-BR), Portuguese Portugal (pt), Spanish (es), Swedish (sv)

<br>

[![Lokalise](docs/Lokalise.png)](https://lokalise.com/)<br>
Thanks to Lokalise, this project manages translations hassle-free. Head over to the [translations section](#contributing) to see how you can contribute — it's super easy, I promise!

### Entities

This integration will give you about 70 entities!

> [!NOTE]
> Some entities may only be available if supported by your car.

#### Binary sensors

- Diagnostics: car availability, service, washer fluid, brake fluid
- Doors open/closed: front, back, hood, tailgate, tank lid
- Engine status: running, coolant level, oil level
- Light warnings: brakes, daytime lights, fog lights, hazard lights, high & low beam lights, position lights, registration plate, reverse light, side mark lights, turn indicators
- Tyre pressure warnings
- Windows open/closed: front, back, sunroof

Some sensors provide extra information in the attributes, like reason, pressure or level.

#### Buttons

- Start/stop climatization
- Flash
- Honk
- Honk & flash

The action's status is included in the attributes.

#### Tracking

- Location tracking, including heading direction

#### Images

- Multiple exterior images from different angles
- Interior

#### Locks

- Lock
- Lock with reduced guard
- Unlock

The action's status is included in the attributes.

#### Sensors

- Energy and/or fuel consumption
- Average speed
- Fuel amount
- Battery capacity
- Battery charge level
- Charging connection
- Charging status
- Estimated charging time
- Distance to empty battery / tank
- Distance to service
- Engine hours to service
- Time to service
- Odometer
- Trip meter

#### Attributes

Most entities have these attributes:

- `api_timestamp`: Timestamp indicating the last time the API retrieved the value from the vehicle.

#### Additional entities

| Entity               | Type   | Description                                                                                                                                 |
| -------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| API status           | Sensor | Gives an indication if the Volvo API is online.                                                                                             |
| API request counter  | Sensor | Shows the number of requests made by this integration.                                                                                      |
| Data update interval | Number | Set the data update interval. Default is 135 seconds. Volvo gives you 10.000 requests a day (per API key), so you may want to do some math! |
| Update data          | Button | Force a data refresh.                                                                                                                       |

## 🤖 Actions

The integration allows you to refresh all data, or only specific parts of the data, by using the `Refresh data` action. This action can be used in automations.

Triggering a data refresh with this action will reset the current refresh timer, postponing the next scheduled full data refresh.

## 🛠️ Installation

### Requirements

- [Home Assistant](https://www.home-assistant.io/) v2024.11.0 or later.

- [Home Assistant Community Store (HACS)](https://hacs.xyz/).

- You'll also need a Volvo developer account to use this integration. Don't worry, it's free of charge!

  1. Head over to https://developer.volvocars.com/ and make an account. Make sure to use the same e-mail address as your Volvo Id.
  2. Once signed in, go to https://developer.volvocars.com/account/#your-api-applications and create an "API application". Give it some meaningful name.
  3. Repeat step 2 for every additional car **on this account** that you'd like to use with this integration. Repeat the whole process if you have cars on different accounts.

### Install

Add this repository to your HACS with the following button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thomasddn&repository=ha-volvo-cars&category=integration)

Install this integration with the follwing button:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=volvo_cars)

### Adding your car

Adding your car involves two steps. You'll need to repeat this process for each car you want to add, even if they are on the same account.

Remember to generate an API key for every car. There is a limit on the number of API requests per key.

#### Step 1: fill in credentials

| Field                         | Description                                                                                           |
| ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| Username                      | The username of your Volvo Id account.                                                                |
| Password                      | The password of your Volvo Id account.                                                                |
| Vehicle Identification Number | The VIN of the car you want to add.                                                                   |
| Volvo API key                 | The generated API key in the developer account.                                                       |
| Friendly name                 | This value is used in the entity ID (volvo\_[friendly name]\_[key]). If left empty, VIN will be used. |

After submitting, a One Time Password (OTP) will be sent to your email. It's a 6 digit number.

#### Step 2: OTP

Fill in the OTP to complete the process.

### Options

Once a car has been added, you can configure additional options for it.

| Option                        | Description                                                               | Availability                                          |
| ----------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------- |
| Volvo API key                 | The generated API key in the developer account.                           |                                                       |
| Device tracker picture        | The picture that will be shown on the map.                                |                                                       |
| Energy consumption unit       | You can choose between `kWh/100 km` and `mi/kWh`.                         | Cars with a battery engine.                           |
| Fuel consumption unit         | You can choose between `l/100 km`, `mpg (UK)` and `mpg (US)`              | Cars with a combustion engine.                        |
| Images transparent background | Whether or not you want transparent a background for the exterior images. | Depending on the image URL provided by the Volvo API. |
| Images background color       | Choose the background color for the exterior images.                      | Depending on the image URL provided by the Volvo API. |

## 🛟 Need help?

Make sure to [read the FAQ](https://github.com/thomasddn/ha-volvo-cars/wiki/FAQ) first. Maybe the topic is covered there.

If you have a feature request or encounter a problem, feel free to open an issue! Have a general question, need help setting up, or want to show off your Volvo dashboard? Go to the discussions.

You can also join the [thread on the HA community](https://community.home-assistant.io/t/volvo-cars-integration/796417/).

<a name="contributing"></a>

## 🤝 Contributing

### General

To everyone who tested, broke things, reported bugs, shared ideas, and gave feedback — y'all are the<br>dream team! 🙌

If you stumble upon a bug, or have an idea to improve this integration, you may always submit a pull request.

### Translations

Would you like to see the labels in your own language? Or perhaps you've spotted a typo or grammatical error that needs fixing? Hop over to [the Lokalise project](https://app.lokalise.com/public/7821992667866be0aaf3d4.04682215/) to manage translations. Alternatively you can create a "translation" issue to request a change.

Thanks for the idea, [ivanfmartinez](https://github.com/ivanfmartinez)! 🔡

### Testing

Shoutout to [Pau1ey](https://github.com/thomasddn/ha-volvo-cars/issues/1#issuecomment-2540446206) for testing and confirming this! 🤩

- ~~Test if you have multiple Volvos across **different accounts**.~~
- ~~Test with other Volvo models (non-BEV).~~
- ~~Users that use imperial system.~~

Both [timthorn](https://community.home-assistant.io/t/volvo-cars-integration/796417/73) and [dalvald](https://github.com/thomasddn/ha-volvo-cars/discussions/3#discussioncomment-11754676) rocking two cars on the same account, what a flex! 💪

- ~~Test if you have multiple Volvos on the **same account**.~~

<a name="sponsor"></a>

## 🚗 Powered by dreams

If you'd like to show your appreciation for this project, feel free to toss a coin to your dev. Donations help keep things running — and who knows, maybe one day they'll add up to a Volvo EX90 (hey, let me dream!). If you're feeling generous, you may donate one too — I'll even come pick it up! 😁

[![ko-fi sponsor][kofi-sponsor-shield]][kofi-sponsor]
[![github sponsor][github-sponsor-shield]][github-sponsor]

[releases-shield]: https://img.shields.io/github/v/release/thomasddn/ha-volvo-cars?style=flat-square
[downloads-shield]: https://img.shields.io/github/downloads/thomasddn/ha-volvo-cars/total?style=flat-square
[releases]: https://github.com/thomasddn/ha-volvo-cars/releases
[ci-dev-shield]: https://img.shields.io/github/actions/workflow/status/thomasddn/ha-volvo-cars/ci.yml?branch=develop&style=flat-square&label=develop
[ci-main-shield]: https://img.shields.io/github/actions/workflow/status/thomasddn/ha-volvo-cars/ci.yml?branch=main&style=flat-square&label=main
[ci-workflow]: https://github.com/thomasddn/ha-volvo-cars/actions/workflows/ci.yml
[hacs-shield]: https://img.shields.io/badge/HACS-default-blue?style=flat-square
[hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=thomasddn&repository=ha-volvo-cars&category=integration
[sponsor-shield]: https://img.shields.io/static/v1?label=sponsor&message=%E2%9D%A4&color=%23fe8e86&style=flat-square
[kofi-sponsor-shield]: https://img.shields.io/badge/Support_me_on_Ko--fi-%E2%9D%A4-fe8e86?style=for-the-badge&logo=kofi&logoColor=ffffff
[kofi-sponsor]: https://ko-fi.com/N4N7UZ6KN
[github-sponsor-shield]: https://img.shields.io/badge/Support_me_on_GitHub-%E2%9D%A4-fe8e86?style=for-the-badge&logo=github&color=fe8e86
[github-sponsor]: https://github.com/sponsors/thomasddn
