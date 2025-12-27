# Referral Program

The application includes a referral system that rewards users for inviting others to the platform.

## Incentive: Refer 5, Get 6 Months Free

When a user successfully refers **5 new users**, they are automatically rewarded with **6 months of the Plus Tier subscription for free**.

### How it works

1.  **Referral Code**: Each user has a unique referral code.
2.  **Invitation**: Users share their code with potential new users.
3.  **Redemption**: When a new user signs up (or enters the code in their settings), they apply the referral code.
4.  **Tracking**: The system tracks the number of successful referrals for each referrer.
5.  **Reward Trigger**:
    *   Once the referrer's count reaches **5**, the system automatically grants the reward.
    *   **New Subscription**: If the referrer is on the Free tier, they are upgraded to the Plus tier for 6 months.
    *   **Existing Subscription**: If the referrer already has a Plus tier subscription, their subscription end date is extended by 6 months.

### Technical Implementation

The logic is handled in `src/api/services/referral_service.py` within the `apply_referral` method. When the referral count increments to 5, the `grant_referral_reward` method is called to update the `UserSubscriptions` table.
