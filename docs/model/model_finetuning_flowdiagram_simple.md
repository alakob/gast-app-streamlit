```mermaid
graph TD
    %% Main Process Flow
    START[Start Fine-tuning Process] --> CONFIG[Load Configuration Settings]
    CONFIG --> CONNECT[Connect to External Services]
    CONNECT --> DATA_LOAD[Load Genetic Data]
    DATA_LOAD --> DATA_PROC[Process & Balance Data]
    DATA_PROC --> MODEL_SETUP[Set Up AI Model]
    MODEL_SETUP --> TRAINING[Train Model]
    TRAINING --> EVALUATE[Evaluate Results]
    EVALUATE --> DEPLOY[Deploy Trained Model]
    
    %% Data Processing Flow
    subgraph DataHandling[Genetic Data Processing]
        AMR_FILES[AMR-Positive Sequences] --> LOAD_AMR[Extract AMR Sequences]
        NON_AMR_FILES[AMR-Negative Sequences] --> LOAD_NON_AMR[Extract Non-AMR Sequences]
        LOAD_AMR --> DATASET_CREATE[Create Balanced Dataset]
        LOAD_NON_AMR --> DATASET_CREATE
        DATASET_CREATE --> SPLIT[Split into Training Sets]
        SPLIT --> PREPARE[Prepare for AI Processing]
    end
    
    DATA_LOAD --> AMR_FILES
    DATA_LOAD --> NON_AMR_FILES
    DATA_PROC --> DATASET_CREATE
    DATA_PROC --> SPLIT
    DATA_PROC --> PREPARE
    
    %% Model Configuration
    subgraph ModelSetup[AI Model Configuration]
        BASE[Select Base AI Model]
        ADAPT[Apply Efficient Adaptation]
        CONFIG_MODEL[Configure Model Parameters]
        
        BASE --> ADAPT
        ADAPT --> CONFIG_MODEL
    end
    
    MODEL_SETUP --> BASE
    MODEL_SETUP --> ADAPT
    MODEL_SETUP --> CONFIG_MODEL
    
    %% Training Process
    subgraph TrainingProcess[Training Process]
        BALANCE[Apply Class Balancing]
        TRAIN_CONFIG[Set Training Parameters]
        EXECUTE[Execute Training]
        MONITOR[Monitor Progress]
        
        BALANCE --> TRAIN_CONFIG
        TRAIN_CONFIG --> EXECUTE
        EXECUTE --> MONITOR
    end
    
    TRAINING --> BALANCE
    TRAINING --> TRAIN_CONFIG
    TRAINING --> EXECUTE
    TRAINING --> MONITOR
    
    %% Evaluation
    subgraph Evaluation[Model Evaluation]
        TEST[Test Model Performance]
        MEASURE[Calculate Accuracy Metrics]
        REPORT[Generate Performance Report]
        
        TEST --> MEASURE
        MEASURE --> REPORT
    end
    
    EVALUATE --> TEST
    EVALUATE --> MEASURE
    EVALUATE --> REPORT
    
    %% External Services
    subgraph ExternalTools[External Services]
        MODEL_REPO[AI Model Repository]
        TRACKING[Performance Tracking Service]
        SHARING[Model Sharing Platform]
        
        MODEL_REPO --> SHARING
        TRACKING --> SHARING
    end
    
    CONNECT --> MODEL_REPO
    CONNECT --> TRACKING
    DEPLOY --> SHARING
    MONITOR --> TRACKING
    
    %% Data Flow
    subgraph DataFlow[Data Transformation]
        direction LR
        RAW[Raw Genetic Sequences] --> LABELED[Labeled Sequences]
        LABELED --> TOKENIZED[AI-Ready Sequences]
        TOKENIZED --> TRAINED[Trained Model]
        TRAINED --> METRICS[Performance Metrics]
    end
    
    %% Visual Styling
    classDef process fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef data fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
    classDef model fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c
    classDef service fill:#fffde7,stroke:#ffd600,color:#ff6f00
    classDef start fill:#b9f6ca,stroke:#00c853,color:#004d40,font-weight:bold
    classDef end fill:#ffccbc,stroke:#ff3d00,color:#bf360c,font-weight:bold
    
    class START,CONFIG,CONNECT,DATA_LOAD,DATA_PROC,MODEL_SETUP,TRAINING,EVALUATE,DEPLOY process
    class AMR_FILES,NON_AMR_FILES,LOAD_AMR,LOAD_NON_AMR,DATASET_CREATE,SPLIT,PREPARE,RAW,LABELED,TOKENIZED data
    class BASE,ADAPT,CONFIG_MODEL,BALANCE,TRAIN_CONFIG,EXECUTE,MONITOR,TRAINED model
    class MODEL_REPO,TRACKING,SHARING,TEST,MEASURE,REPORT,METRICS service
    class START start
    class DEPLOY end
```