from executive_worker.task_tree import TaskTree, TaskNode


def test_task_tree_create_and_reload(tmp_path):
    repo_root = tmp_path

    tree = TaskTree.load_or_create(str(repo_root), "ticket-1", "Sample Ticket")
    assert tree.id == "ticket-1"
    assert tree.title == "Sample Ticket"

    node = TaskNode(id="n-1", title="Do something")
    tree.add_or_update_node(node)
    tree.save(str(repo_root))

    # Reload and verify persistence
    loaded = TaskTree.load_or_create(str(repo_root), "ticket-1", "Should be ignored")
    assert loaded.id == "ticket-1"
    assert loaded.title == "Sample Ticket"
    assert any(n.id == "n-1" and n.title == "Do something" for n in loaded.nodes)

