from app.models.trace import AgentTrace


def main() -> None:
    columns = AgentTrace.__table__.columns #返回该表所有列的集合

    expected_columns = {
        "id",
        "run_id",
        "step",
        "tool_name",
        "input",
        "output",
        "latency_ms",
        "status",
        "created_at",
    }

    actual_columns = {column.name for column in columns}

    assert AgentTrace.__tablename__ == "agent_traces"
    assert expected_columns.issubset(actual_columns)

    assert AgentTrace.run_id.property.columns[0].index is True
    assert AgentTrace.tool_name.property.columns[0].nullable is True
    assert AgentTrace.output_data.property.columns[0].nullable is True
    assert AgentTrace.status.property.columns[0].nullable is False

    print("AgentTrace 表名:", AgentTrace.__tablename__)
    print("AgentTrace 字段:", sorted(actual_columns))
    print("Day 50 Trace 数据结构检查通过。")


if __name__ == "__main__":
    main()
