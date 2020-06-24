# SLCB Channel Points No Fudges Given

This script allows the user to trigger a timer and some sfx via a custom channel point reward.

## Installing

This script was built for use with Streamlabs Chatbot.
Follow instructions on how to install custom script packs at:
https://github.com/StreamlabsSupport/Streamlabs-Chatbot/wiki/Prepare-&-Import-Scripts

Click [Here](https://github.com/Encrypted-Thoughts/SLCB-ChannelPointsNoFudgesGiven/blob/master/ChannelPointsNoFudges.zip?raw=true) to download the script pack.

Once installed you will need to provide an oAuth token. You can get one by clicking the Get Token button in script settings.

![token](https://user-images.githubusercontent.com/50642352/82402817-f8165480-9a22-11ea-8810-fc93899d785a.png)

You will also need to give the script access to broadcast streamlabs events. This can be achieved by right clicking on the script in Streamlabs Chatbot and selecting "Insert API Key". https://github.com/StreamlabsSupport/Streamlabs-Chatbot/wiki/Script-overlays

![api key](https://user-images.githubusercontent.com/50642352/83985340-7701fd00-a8fe-11ea-9aca-393d6dc7d4b4.png)

After that you should be able to add a new Browser source in OBS and point it to "index.html" located in the "overlay" folder in the script folder. If you're unsure how to locate the streamlabs custom scripts folder you can select "Open Script Folder" shown in the above step.

![index](https://user-images.githubusercontent.com/50642352/85502251-93639200-b5ac-11ea-8ace-0bee0412d122.png)

## Use

Once installed you just need to add custom channel point rewards to your twitch channel and then match the names of the reward to a Twitch Reward event in the script settings.

The script also adds a custom custom command for resetting the timer.
  
!fuckup - this resets the timer to the closest time interval that the countdown is set to run.
!fuckup {some value in seconds} - Adds the value in seconds to the timer. Value can be negative to remove time if necessary.

## Author

EncryptedThoughts - [Twitch](https://www.twitch.tv/encryptedthoughts)

## References

This script makes use of TwitchLib's pubsub listener to detect the channel point redemptions. Go check out their repo at https://github.com/TwitchLib/TwitchLib for more info.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

