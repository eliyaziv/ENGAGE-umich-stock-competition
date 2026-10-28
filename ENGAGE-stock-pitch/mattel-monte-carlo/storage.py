import uuid
import streamlit as st


def create_storage_id():
    return uuid.uuid4().hex
