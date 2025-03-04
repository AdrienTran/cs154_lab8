import pyrtl

main_memory = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name="main_mem")

virtual_addr_i        = pyrtl.Input(bitwidth=32, name="virtual_addr_i")
new_req_i             = pyrtl.Input(bitwidth=1,  name="new_req_i")
reset_i               = pyrtl.Input(bitwidth=1,  name="reset_i")
req_type_i            = pyrtl.Input(bitwidth=1,  name="req_type_i")

physical_addr_o       = pyrtl.Output(bitwidth=32,name="physical_addr_o")
dirty_o               = pyrtl.Output(bitwidth=1, name="dirty_o")
valid_o               = pyrtl.Output(bitwidth=1, name="valid_o")
ref_o                 = pyrtl.Output(bitwidth=1, name="ref_o")
error_code_o          = pyrtl.Output(bitwidth=3, name="error_code_o")
finished_walk_o       = pyrtl.Output(bitwidth=1, name="finished_walk_o")

page_fault          = pyrtl.WireVector(bitwidth=1, name="page_fault")
state               = pyrtl.Register(bitwidth=2, name="state")
base_register       = pyrtl.Const(0x3FFBFF, bitwidth=22)

writable = pyrtl.WireVector(bitwidth=1, name="writable")
readable = pyrtl.WireVector(bitwidth=1, name="readable")

# Step 1 : Split input into the three offsets
offset1 = pyrtl.WireVector(bitwidth=10, name="offset1")
offset2 = pyrtl.WireVector(bitwidth=10, name="offset2")
offset3 = pyrtl.WireVector(bitwidth=12, name="offset3")
offset1 |= virtual_addr_i[22:32]
offset2 |= virtual_addr_i[12:22]
offset3 |= virtual_addr_i[0:12]


# Step 2 : UPDATE STATE according to state diagram in instructions
with pyrtl.conditional_assignment:
    with reset_i == 0:
        with state == 0:
            with new_req_i == 1:
                state.next |= 1
        with state == 1:
            with (page_fault) == 1: # | (~writable & req_type_i) | (~readable & ~req_type_i)
                state.next |= 0
            with page_fault == 0:
                state.next |= 2
        with state == 2:
            state.next |= 0
    with reset_i == 1:
        state.next |= 0

# Step 3 : Determine physical address by walking the page table structure
next_addr = pyrtl.Register(bitwidth=32, name="next_addr")

with pyrtl.conditional_assignment:
    with state == 0:
        next_addr.next |= pyrtl.corecircuits.concat(base_register, offset1)
        # print(temp_addr.bitwidth)
        
    with state == 1:
        first_entry = main_memory[next_addr]
        
        valid = first_entry[31]
        valid_o |= first_entry[31]
        dirty_o |= first_entry[30]
        ref_o |= first_entry[29]
        
        with valid == 0:
            page_fault |= 1
            error_code_o |= 1
        
        next_addr.next |= pyrtl.corecircuits.concat(first_entry[0:22], offset2)
        # print(temp_addr.bitwidth)
        
    with state == 2:
        second_entry = main_memory[next_addr]
        
        valid_o |= second_entry[31]
        dirty_o |= second_entry[30]
        ref_o |= second_entry[29]
        writable |= second_entry[28]
        readable |= second_entry[27]
        
        valid = second_entry[31]
        with valid == 0:
            page_fault |= 1
            error_code_o |= 1
        with req_type_i == 0:
            with readable == 0:
                error_code_o |= 2
        with req_type_i == 1:
            with writable == 0:
                error_code_o |= 4
        
        temp_addr2 = pyrtl.corecircuits.concat(second_entry[0:20], offset3)
        # print(temp_addr.bitwidth)
        # temp_addr = temp_addr | offset3
        
        physical_addr_o |= temp_addr2
        finished_walk_o |= 1
        
            

# Step 4 : Determine the outputs based on the last level of the page table walk
# with pyrtl.conditional_assignment:
#     with reset_i == 0:
#         with state == 0:
#             error_code_o |= 0
#         with state == 1:
#             with page_fault == 1:
#                 error_code_o |= 1
#             with page_fault == 0:
#                 error_code_o |= 0
#         with state == 2:
#             finished_walk_o |= 1
#             with page_fault == 1:
#                 error_code_o |= 1
#             with req_type_i == 0:
#                 with readable == 0:
#                     error_code_o |= 2
#             with req_type_i == 1:
#                 with writable == 0:
#                     error_code_o |= 4
#             with pyrtl.otherwise:
#                 error_code_o |= 0
                

                

if __name__ == "__main__":

    """
    These memory addresses correspond to the test that we walk through in the instructions
    This just does a basic walk from the first level to the last level where no errors should occur
    """
    memory = {
        4293918528: 0xC43FFC6B,
        4294029192: 0xAC061D26,
        1641180595: 0xDEADBEEF
    }

    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map={main_memory: memory})

    for i in range(3):
        sim.step({
            new_req_i: 1,
            reset_i: 0,
            virtual_addr_i: 0xD0388DB3,
            req_type_i: 0
    })

    sim_trace.render_trace(symbol_len=20)

    assert (sim_trace.trace["physical_addr_o"][-1] == 0x61d26db3)
    assert (sim_trace.trace["error_code_o"][-1] == 0x0)
    assert (sim_trace.trace["dirty_o"][-1] == 0x0)
    
