import met_preprocessor.standard_param as standard_param
import met_preprocessor.opt_param as opt_param
import itertools


def process_dependencies(param_map):
    """Lists set of possible dependencies and their callable functions
    for a param."""
    dependencies = {}
    for param, param_info in param_map.items():
        ans = []
        for pi_calc in param_info.get("calc", []):
            param_type = {
                "standard" : standard_param,
                "optional" : opt_param
            }
            try:
                func = getattr(param_type[param_info["type"]], pi_calc["func"])
            except KeyError:
                raise Exception("Not yet defined for just conversion params")

            parsed_deps = pi_calc.get("deps", "").split(",")
            ans.append((parsed_deps, func))
        dependencies[param] = ans

    return dependencies



def cycle_check(node: str, visited: dict[str, bool], adj_list: dict[str, list[str]]):
    """Cycle checks using DFS."""

    # Already visited node
    if visited.get(node):
        return True

    visited[node] = True
    res = any([cycle_check(dep, visited, adj_list) for dep in adj_list.get(node, [])])
    if not res:
        del visited[node]

    return res


def replace_tup(tup_list, val, new_tup):
    for i, tup in enumerate(tup_list):
        if tup[0] == val:
            tup_list[i] = new_tup
            return tup_list
    return tup_list + [new_tup]


def order_load_dep(res, dependencies, input_list):
    """
    Given a Directed Acyclic Graph, convert which order to calculate values.
    Eg: input_list = {1, 3}  dependencies = {2 : [[1, 4], [1, 3]], 4 : 1}
    Here answer should be {4 : [1] , 2 : [1, 4]} based on priority
    """
    for param, dep_list in dependencies.items():
        for i, (deps, func) in enumerate(dep_list):
            if set(deps).issubset(set(input_list)):
                # Remove on/after param
                dependencies[param] = dependencies[param][:i]
                # Replace param in res if present otherwise append
                updated_res = replace_tup(res, param, (param, deps, func))
                return order_load_dep(updated_res, dependencies, input_list + [param])
    # If no extra dependencies found, then return the accumulated result
    return res


def generate_calculations(dataset, param_map):
    pd = process_dependencies(param_map)
    is_cycle_chain = {
        k: list(set(itertools.chain.from_iterable([vi[0] for vi in v])))
        for k, v in pd.items()
    }
    for node in pd.keys():
        if cycle_check(node, {}, is_cycle_chain):
            raise Exception(f"Circular dependency detected near {node}")
    return order_load_dep([], pd, list(dataset.keys()) + ["none"])
