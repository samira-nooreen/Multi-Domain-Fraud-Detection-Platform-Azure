"""
Fake Profile/Bot Detection - Enhanced Dataset Generator
Generates realistic user profiles with bot and human behavior patterns,
including social graph structures and temporal activity sequences.
"""
import pandas as pd
import numpy as np
import random
import os

# Set seeds for reproducibility
np.random.seed(42)
random.seed(42)

def generate_full_dataset(n_users=2000):
    print(f"Generating data for {n_users} users...")
    
    # ---------------------------------------------------------
    # 1. Generate Base Profile Data (Tabular)
    # ---------------------------------------------------------
    data = []
    user_ids = list(range(n_users))
    
    # 30% Bots, 70% Humans
    labels = np.random.choice([0, 1], size=n_users, p=[0.7, 0.3])
    
    for user_id, is_bot in zip(user_ids, labels):
        if is_bot:
            # BOT PATTERNS - More varied
            bot_type = random.choice(['spam_bot', 'follower_bot', 'engagement_bot'])
            
            if bot_type == 'spam_bot':
                # High activity, many posts
                followers = random.randint(0, 50)
                following = random.randint(1000, 5000)
                posts = random.randint(2000, 10000)
                age_days = random.randint(1, 60)
            elif bot_type == 'follower_bot':
                # Follows many, few posts
                followers = random.randint(0, 100)
                following = random.randint(500, 3000)
                posts = random.randint(0, 100)  # Can have few posts
                age_days = random.randint(1, 90)
            else:  # engagement_bot
                # Moderate following, high engagement
                followers = random.randint(10, 200)
                following = random.randint(200, 1000)
                posts = random.randint(100, 1000)
                age_days = random.randint(5, 120)
            
            verified = 0
            profile_completeness = random.uniform(0.0, 0.5)
            bio_length = random.randint(0, 40)
            likes_per_post = random.uniform(0.0, 3.0)
            ip_diversity = random.randint(1, 2)
        else:
            # HUMAN PATTERNS - More varied including edge cases
            user_type = random.choice(['active', 'lurker', 'new_user', 'casual'])
            
            if user_type == 'active':
                # Regular active users
                followers = random.randint(100, 2000)
                following = random.randint(100, 1000)
                posts = random.randint(50, 500)
                age_days = random.randint(180, 3650)
                profile_completeness = random.uniform(0.7, 1.0)
                bio_length = random.randint(50, 200)
            elif user_type == 'lurker':
                # Legitimate users who don't post much (IMPORTANT FOR YOUR CASE)
                followers = random.randint(50, 800)
                following = random.randint(100, 800)
                posts = random.randint(0, 10)  # Few or no posts
                age_days = random.randint(90, 2000)
                profile_completeness = random.uniform(0.5, 0.9)
                bio_length = random.randint(0, 100)  # Can have short bio
            elif user_type == 'new_user':
                # New legitimate accounts
                followers = random.randint(10, 200)
                following = random.randint(20, 300)
                posts = random.randint(0, 20)
                age_days = random.randint(1, 90)
                profile_completeness = random.uniform(0.4, 0.8)
                bio_length = random.randint(0, 80)
            else:  # casual
                # Casual users
                followers = random.randint(50, 500)
                following = random.randint(50, 600)
                posts = random.randint(5, 100)
                age_days = random.randint(180, 1500)
                profile_completeness = random.uniform(0.6, 0.9)
                bio_length = random.randint(20, 150)
            
            verified = np.random.choice([0, 1], p=[0.95, 0.05])
            likes_per_post = random.uniform(5.0, 50.0)
            ip_diversity = random.randint(1, 10)

        # Derived features
        ratio = followers / max(following, 1)
        freq = posts / max(age_days, 1)
        
        data.append({
            'user_id': user_id,
            'followers': followers,
            'following': following,
            'posts': posts,
            'age_days': age_days,
            'verified': verified,
            'follower_following_ratio': ratio,
            'avg_posts_per_day': freq,
            'profile_completeness': profile_completeness,
            'bio_length': bio_length,
            'likes_per_post': likes_per_post,
            'ip_diversity': ip_diversity,
            'label': is_bot
        })
    
    df_profiles = pd.DataFrame(data)
    
    # ---------------------------------------------------------
    # 2. Generate Social Graph (Edges for GNN)
    # ---------------------------------------------------------
    edges = []
    
    # Create bot farm (bots following bots)
    bots = df_profiles[df_profiles['label'] == 1]['user_id'].values
    humans = df_profiles[df_profiles['label'] == 0]['user_id'].values
    
    # Bots following random humans (spam following)
    for bot in bots:
        # Each bot follows 20-50 random humans
        targets = np.random.choice(humans, size=random.randint(20, 50), replace=False)
        for t in targets:
            edges.append([bot, t])
            
        # Bots following other bots (dense cluster)
        if len(bots) > 10:
            targets_bots = np.random.choice(bots, size=random.randint(5, 15), replace=False)
            for t in targets_bots:
                if bot != t:
                    edges.append([bot, t])

    # Humans following humans (communities)
    # Create a few "communities"
    communities = np.array_split(humans, 5)
    for community in communities:
        for human in community:
            # Follow people in same community
            if len(community) > 1:
                targets = np.random.choice(community, size=random.randint(5, 20), replace=False)
                for t in targets:
                    if human != t:
                        edges.append([human, t])
            
            # Follow some randoms outside
            targets_out = np.random.choice(humans, size=random.randint(1, 5), replace=False)
            for t in targets_out:
                if human != t:
                    edges.append([human, t])

    df_edges = pd.DataFrame(edges, columns=['source', 'target'])
    
    # ---------------------------------------------------------
    # 3. Generate Temporal Sequences (for LSTM)
    # ---------------------------------------------------------
    # Sequence length: 10 time steps
    # Features per step: [posts_count, likes_given, follows_count, active_seconds]
    seq_len = 10
    n_features = 4
    sequences = np.zeros((n_users, seq_len, n_features))
    
    for i, is_bot in enumerate(labels):
        if is_bot:
            # Bot: Regular, high activity, low variance
            base_posts = random.randint(5, 20)
            for t in range(seq_len):
                sequences[i, t, 0] = base_posts + random.randint(-1, 1) # Posts
                sequences[i, t, 1] = random.randint(0, 5) # Likes given (low)
                sequences[i, t, 2] = random.randint(10, 50) # Follows (high)
                sequences[i, t, 3] = 3600 * 24 # Active all day (seconds)
        else:
            # Human: Irregular, bursts, sleep cycles
            for t in range(seq_len):
                if random.random() < 0.2: # Inactive day
                    sequences[i, t, :] = 0
                else:
                    sequences[i, t, 0] = random.randint(0, 3) # Posts
                    sequences[i, t, 1] = random.randint(5, 50) # Likes given
                    sequences[i, t, 2] = random.randint(0, 2) # Follows
                    sequences[i, t, 3] = random.randint(600, 10000) # Active seconds

    return df_profiles, df_edges, sequences, labels

if __name__ == "__main__":
    print("Generating enhanced datasets...")
    
    df, edges, seqs, labels = generate_full_dataset(2000)
    
    # Save files
    df.to_csv('profile_data.csv', index=False)
    edges.to_csv('social_edges.csv', index=False)
    
    # Save nodes (just user IDs for now, GNN will use profile features)
    nodes = pd.DataFrame({'user_id': df['user_id']})
    nodes.to_csv('social_nodes.csv', index=False)
    
    # Save temporal data
    np.save('temporal_sequences.npy', seqs)
    np.save('temporal_labels.npy', labels)
    
    print(f"✓ Saved profile_data.csv ({len(df)} rows)")
    print(f"  - Humans: {len(df[df['label']==0])}")
    print(f"  - Bots: {len(df[df['label']==1])}")
    print(f"✓ Saved social_edges.csv ({len(edges)} edges)")
    print(f"✓ Saved temporal_sequences.npy ({seqs.shape})")
    print("Done!")
