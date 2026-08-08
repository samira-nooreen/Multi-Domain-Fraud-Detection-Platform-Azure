"""
Fake Profile Detection using Graph Neural Network (GNN)
"""
import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.data import Data, DataLoader
from torch_geometric.nn import GCNConv, global_mean_pool
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Check if CUDA is available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

class GNNProfileDetector(torch.nn.Module):
    def __init__(self, num_node_features, hidden_dim=64):
        super(GNNProfileDetector, self).__init__()
        self.conv1 = GCNConv(num_node_features, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.conv3 = GCNConv(hidden_dim, hidden_dim)
        self.fc1 = torch.nn.Linear(hidden_dim, 32)
        self.fc2 = torch.nn.Linear(32, 2)  # Binary classification
        self.dropout = torch.nn.Dropout(0.5)
    
    def forward(self, x, edge_index, batch):
        # Graph convolutional layers
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.conv3(x, edge_index)
        x = F.relu(x)
        
        # Global pooling
        x = global_mean_pool(x, batch)
        
        # Fully connected layers
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        
        return F.log_softmax(x, dim=1)

def generate_instagram_dataset(n_samples=3000):
    """
    Generate Instagram-style dataset with graph structure
    """
    print(f"Generating {n_samples} Instagram-style profiles with graph structure...")
    
    data = []
    labels = []
    
    # 60% genuine, 40% fake
    n_genuine = int(n_samples * 0.6)
    n_fake = n_samples - n_genuine
    
    # Generate GENUINE users
    for i in range(n_genuine):
        user_type = np.random.choice(['active', 'lurker', 'casual', 'new'])
        
        if user_type == 'active':
            followers = np.random.randint(200, 5000)
            following = np.random.randint(100, 1000)
            posts = np.random.randint(50, 1000)
            bio_length = np.random.randint(50, 150)
            has_profile_pic = 1
        elif user_type == 'lurker':
            followers = np.random.randint(100, 1500)
            following = np.random.randint(200, 1200)
            posts = np.random.randint(0, 20)
            bio_length = np.random.randint(0, 100)
            has_profile_pic = np.random.choice([0, 1], p=[0.2, 0.8])
        elif user_type == 'casual':
            followers = np.random.randint(50, 800)
            following = np.random.randint(50, 600)
            posts = np.random.randint(10, 200)
            bio_length = np.random.randint(20, 120)
            has_profile_pic = 1
        else:  # new
            followers = np.random.randint(10, 300)
            following = np.random.randint(20, 400)
            posts = np.random.randint(0, 30)
            bio_length = np.random.randint(0, 80)
            has_profile_pic = np.random.choice([0, 1], p=[0.3, 0.7])
        
        # Derived features
        follower_ratio = followers / max(following, 1)
        engagement_score = posts * 0.5 + followers * 0.3 + following * 0.2
        
        data.append({
            'followers_count': followers,
            'friends_count': following,
            'statuses_count': posts,
            'bio_length': bio_length,
            'has_profile_pic': has_profile_pic,
            'follower_ratio': follower_ratio,
            'engagement_score': engagement_score
        })
        labels.append(1)  # Genuine
    
    # Generate FAKE users
    for i in range(n_fake):
        bot_type = np.random.choice(['spam', 'follower_farm', 'engagement'])
        
        if bot_type == 'spam':
            followers = np.random.randint(0, 100)
            following = np.random.randint(1000, 5000)
            posts = np.random.randint(500, 5000)
            bio_length = np.random.randint(0, 30)
            has_profile_pic = np.random.choice([0, 1], p=[0.6, 0.4])
        elif bot_type == 'follower_farm':
            followers = np.random.randint(0, 200)
            following = np.random.randint(500, 3000)
            posts = np.random.randint(0, 100)
            bio_length = np.random.randint(0, 40)
            has_profile_pic = np.random.choice([0, 1], p=[0.5, 0.5])
        else:  # engagement
            followers = np.random.randint(50, 500)
            following = np.random.randint(200, 1500)
            posts = np.random.randint(100, 1000)
            bio_length = np.random.randint(0, 50)
            has_profile_pic = 1
        
        follower_ratio = followers / max(following, 1)
        engagement_score = posts * 0.5 + followers * 0.3 + following * 0.2
        
        data.append({
            'followers_count': followers,
            'friends_count': following,
            'statuses_count': posts,
            'bio_length': bio_length,
            'has_profile_pic': has_profile_pic,
            'follower_ratio': follower_ratio,
            'engagement_score': engagement_score
        })
        labels.append(0)  # Fake
    
    return pd.DataFrame(data), np.array(labels)

def create_graph_data(df, labels):
    """Convert tabular data to graph data"""
    graph_data_list = []
    
    for i in range(len(df)):
        # Node features (each user is a single node with all features)
        x = torch.tensor([[
            df.iloc[i]['followers_count'],
            df.iloc[i]['friends_count'],
            df.iloc[i]['statuses_count'],
            df.iloc[i]['bio_length'],
            df.iloc[i]['has_profile_pic'],
            df.iloc[i]['follower_ratio'],
            df.iloc[i]['engagement_score']
        ]], dtype=torch.float)
        
        # Simple self-loop edge for single node graph
        edge_index = torch.tensor([[0], [0]], dtype=torch.long)
        
        # Label
        y = torch.tensor([labels[i]], dtype=torch.long)
        
        # Create graph data object
        data = Data(x=x, edge_index=edge_index, y=y)
        graph_data_list.append(data)
    
    return graph_data_list

def train_gnn_model():
    """Train GNN model for fake profile detection"""
    print("\n=== Training GNN Fake Profile Detection Model ===\n")
    
    # Generate dataset
    df, labels = generate_instagram_dataset(3000)
    
    # Convert to graph data
    print("Converting data to graph format...")
    graph_data = create_graph_data(df, labels)
    
    # Split data
    train_data, test_data = train_test_split(graph_data, test_size=0.2, random_state=42, stratify=labels)
    
    print(f"\nTraining set: {len(train_data)} samples")
    print(f"Test set: {len(test_data)} samples")
    
    # Create data loaders
    train_loader = DataLoader(train_data, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=32, shuffle=False)
    
    # Initialize model
    model = GNNProfileDetector(num_node_features=7).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    
    # Training loop
    print("\nTraining GNN model...")
    model.train()
    for epoch in range(100):  # 100 epochs
        total_loss = 0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            out = model(batch.x, batch.edge_index, batch.batch)
            loss = F.nll_loss(out, batch.y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        if epoch % 20 == 0:
            print(f'Epoch {epoch}, Loss: {total_loss/len(train_loader):.4f}')
    
    # Evaluation
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch in test_loader:
            batch = batch.to(device)
            out = model(batch.x, batch.edge_index, batch.batch)
            pred = out.argmax(dim=1)
            all_preds.extend(pred.cpu().numpy())
            all_labels.extend(batch.y.cpu().numpy())
    
    accuracy = accuracy_score(all_labels, all_preds)
    
    print(f"\n=== Model Performance ===")
    print(f"Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print("\nClassification Report:")
    print(classification_report(all_labels, all_preds, target_names=['Fake', 'Genuine']))
    
    # Save model
    print("\nSaving model...")
    torch.save(model.state_dict(), 'fake_profile_gnn_model.pth')
    joblib.dump(list(df.columns), 'feature_columns.pkl')
    print("✅ GNN model saved successfully!")
    
    return model

if __name__ == "__main__":
    train_gnn_model()
