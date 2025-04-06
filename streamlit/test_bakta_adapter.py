#!/usr/bin/env python3
import streamlit as st
import os
import sys

# Add paths if needed
sys.path.append('/app')

# Try to import our adapter
try:
    from amr_predictor.bakta.unified_adapter import get_adapter, run_async
    adapter_available = True
except ImportError as e:
    st.error(f'Failed to import adapter: {e}')
    adapter_available = False

# Setup page
st.title('Bakta Adapter Test')

# Show environment
st.header('Environment')
env_vars = {k: v for k, v in os.environ.items() if 'BAKTA' in k}
st.json(env_vars)

# Test adapter
if adapter_available:
    st.header('Adapter Test')
    adapter = get_adapter()
    st.success('✓ Adapter created successfully')
    st.write(f'API URL: {adapter.base_url}')
    
    if st.button('Submit Test Job'):
        # Simple test sequence
        sequence = '>Test\nACGTACGTACGT'
        config = {'name': 'test_job', 'genus': 'Test', 'species': 'test'}
        
        try:
            with st.spinner('Submitting test job...'):
                result = run_async(adapter.submit_job, sequence, config)
            
            st.success('Job submitted successfully!')
            st.json(result)
        except Exception as e:
            st.error(f'Error submitting job: {e}')
else:
    st.error('Adapter not available')
